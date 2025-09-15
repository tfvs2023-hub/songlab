"""
SongLab 딥러닝 모델 학습 스크립트
"""

import os
import json
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torch.utils.tensorboard import SummaryWriter
import numpy as np
from pathlib import Path
import argparse
from tqdm import tqdm
import logging
from typing import Dict, Tuple
import matplotlib.pyplot as plt
import seaborn as sns

from data_pipeline import DataCollector, VocalDataset
from model import VocalAnalyzer, VocalAnalyzerLoss, VocalAnalyzerConfig

class Trainer:
    """딥러닝 모델 학습 클래스"""
    
    def __init__(self, config: VocalAnalyzerConfig, experiment_name: str = "vocal_analyzer"):
        self.config = config
        self.experiment_name = experiment_name
        
        # 디렉토리 설정
        self.experiment_dir = Path(f"experiments/{experiment_name}")
        self.experiment_dir.mkdir(parents=True, exist_ok=True)
        
        self.checkpoint_dir = self.experiment_dir / "checkpoints"
        self.checkpoint_dir.mkdir(exist_ok=True)
        
        self.log_dir = self.experiment_dir / "logs"
        self.log_dir.mkdir(exist_ok=True)
        
        # 로깅 설정
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_dir / 'training.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # TensorBoard
        self.writer = SummaryWriter(self.log_dir)
        
        # 디바이스 설정
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.logger.info(f"Using device: {self.device}")
        
        # 모델 초기화
        self.model = VocalAnalyzer(
            audio_length=config.audio_length,
            feature_dim=config.feature_dim,
            num_axes=config.num_axes
        ).to(self.device)
        
        # 손실 함수
        self.criterion = VocalAnalyzerLoss(
            main_weight=config.main_weight,
            axis_weight=config.axis_weight,
            consistency_weight=config.consistency_weight
        )
        
        # 옵티마이저
        self.optimizer = optim.AdamW(
            self.model.parameters(),
            lr=config.learning_rate,
            weight_decay=config.weight_decay
        )
        
        # 스케줄러
        self.scheduler = optim.lr_scheduler.StepLR(
            self.optimizer,
            step_size=config.scheduler_step_size,
            gamma=config.scheduler_gamma
        )
        
        # Early stopping 변수
        self.best_val_loss = float('inf')
        self.patience_counter = 0
        self.start_epoch = 0
        
        # 메트릭 저장
        self.train_losses = []
        self.val_losses = []
        self.train_metrics = []
        self.val_metrics = []
        
    def save_config(self):
        """설정 저장"""
        config_dict = {
            'audio_length': self.config.audio_length,
            'feature_dim': self.config.feature_dim,
            'num_axes': self.config.num_axes,
            'batch_size': self.config.batch_size,
            'learning_rate': self.config.learning_rate,
            'weight_decay': self.config.weight_decay,
            'num_epochs': self.config.num_epochs,
            'main_weight': self.config.main_weight,
            'axis_weight': self.config.axis_weight,
            'consistency_weight': self.config.consistency_weight,
            'scheduler_step_size': self.config.scheduler_step_size,
            'scheduler_gamma': self.config.scheduler_gamma,
            'patience': self.config.patience,
            'min_delta': self.config.min_delta
        }
        
        with open(self.experiment_dir / 'config.json', 'w') as f:
            json.dump(config_dict, f, indent=2)
    
    def save_checkpoint(self, epoch: int, is_best: bool = False):
        """체크포인트 저장"""
        checkpoint = {
            'epoch': epoch,
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'scheduler_state_dict': self.scheduler.state_dict(),
            'best_val_loss': self.best_val_loss,
            'train_losses': self.train_losses,
            'val_losses': self.val_losses,
            'config': self.config.__dict__
        }
        
        # 일반 체크포인트
        torch.save(checkpoint, self.checkpoint_dir / f'checkpoint_epoch_{epoch}.pth')
        
        # 최신 체크포인트
        torch.save(checkpoint, self.checkpoint_dir / 'latest.pth')
        
        # 최고 성능 체크포인트
        if is_best:
            torch.save(checkpoint, self.checkpoint_dir / 'best.pth')
            self.logger.info(f"새로운 최고 성능 모델 저장 (epoch {epoch})")
    
    def load_checkpoint(self, checkpoint_path: str):
        """체크포인트 로드"""
        if os.path.exists(checkpoint_path):
            checkpoint = torch.load(checkpoint_path, map_location=self.device)
            
            self.model.load_state_dict(checkpoint['model_state_dict'])
            self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
            self.scheduler.load_state_dict(checkpoint['scheduler_state_dict'])
            
            self.start_epoch = checkpoint['epoch'] + 1
            self.best_val_loss = checkpoint['best_val_loss']
            self.train_losses = checkpoint.get('train_losses', [])
            self.val_losses = checkpoint.get('val_losses', [])
            
            self.logger.info(f"체크포인트 로드: {checkpoint_path} (epoch {checkpoint['epoch']})")
            return True
        return False
    
    def calculate_metrics(self, predictions: torch.Tensor, targets: torch.Tensor) -> Dict:
        """메트릭 계산"""
        with torch.no_grad():
            # MSE per axis
            mse_per_axis = torch.mean((predictions - targets) ** 2, dim=0)
            
            # MAE per axis
            mae_per_axis = torch.mean(torch.abs(predictions - targets), dim=0)
            
            # Overall metrics
            mse_overall = torch.mean(mse_per_axis)
            mae_overall = torch.mean(mae_per_axis)
            
            # R² score approximation
            ss_res = torch.sum((predictions - targets) ** 2, dim=0)
            ss_tot = torch.sum((targets - torch.mean(targets, dim=0)) ** 2, dim=0)
            r2_per_axis = 1 - (ss_res / (ss_tot + 1e-8))
            r2_overall = torch.mean(r2_per_axis)
            
            metrics = {
                'mse_overall': mse_overall.item(),
                'mae_overall': mae_overall.item(),
                'r2_overall': r2_overall.item(),
                'mse_brightness': mse_per_axis[0].item(),
                'mse_thickness': mse_per_axis[1].item(),
                'mse_loudness': mse_per_axis[2].item(),
                'mse_clarity': mse_per_axis[3].item(),
                'mae_brightness': mae_per_axis[0].item(),
                'mae_thickness': mae_per_axis[1].item(),
                'mae_loudness': mae_per_axis[2].item(),
                'mae_clarity': mae_per_axis[3].item(),
                'r2_brightness': r2_per_axis[0].item(),
                'r2_thickness': r2_per_axis[1].item(),
                'r2_loudness': r2_per_axis[2].item(),
                'r2_clarity': r2_per_axis[3].item(),
            }
            
        return metrics
    
    def train_epoch(self, train_loader: DataLoader, epoch: int) -> Tuple[float, Dict]:
        """한 에포크 학습"""
        self.model.train()
        total_loss = 0.0
        all_predictions = []
        all_targets = []
        
        pbar = tqdm(train_loader, desc=f'Train Epoch {epoch}')
        for batch_idx, batch in enumerate(pbar):
            # 데이터 준비
            audio = batch['audio'].to(self.device)
            features = batch['features'].to(self.device)
            targets = batch['target'].to(self.device)
            
            # Forward pass
            self.optimizer.zero_grad()
            outputs = self.model(audio, features)
            
            # 손실 계산
            loss_dict = self.criterion(outputs, targets)
            loss = loss_dict['total_loss']
            
            # Backward pass
            loss.backward()
            
            # Gradient clipping
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
            
            self.optimizer.step()
            
            # 통계 업데이트
            total_loss += loss.item()
            all_predictions.append(outputs['main_output'].detach().cpu())
            all_targets.append(targets.detach().cpu())
            
            # Progress bar 업데이트
            pbar.set_postfix({
                'loss': f'{loss.item():.4f}',
                'main': f'{loss_dict["main_loss"].item():.4f}',
                'axis': f'{loss_dict["axis_loss"]:.4f}' if isinstance(loss_dict["axis_loss"], torch.Tensor) else f'{loss_dict["axis_loss"]:.4f}',
                'cons': f'{loss_dict["consistency_loss"].item():.4f}' if isinstance(loss_dict["consistency_loss"], torch.Tensor) else f'{loss_dict["consistency_loss"]:.4f}'
            })
            
            # TensorBoard 로깅 (배치 단위)
            global_step = epoch * len(train_loader) + batch_idx
            self.writer.add_scalar('Train/Batch_Loss', loss.item(), global_step)
            self.writer.add_scalar('Train/Learning_Rate', self.optimizer.param_groups[0]['lr'], global_step)
        
        # 에포크 메트릭 계산
        all_predictions = torch.cat(all_predictions, dim=0)
        all_targets = torch.cat(all_targets, dim=0)
        metrics = self.calculate_metrics(all_predictions, all_targets)
        
        avg_loss = total_loss / len(train_loader)
        return avg_loss, metrics
    
    def validate_epoch(self, val_loader: DataLoader, epoch: int) -> Tuple[float, Dict]:
        """한 에포크 검증"""
        self.model.eval()
        total_loss = 0.0
        all_predictions = []
        all_targets = []
        
        with torch.no_grad():
            pbar = tqdm(val_loader, desc=f'Val Epoch {epoch}')
            for batch in pbar:
                # 데이터 준비
                audio = batch['audio'].to(self.device)
                features = batch['features'].to(self.device)
                targets = batch['target'].to(self.device)
                
                # Forward pass
                outputs = self.model(audio, features)
                
                # 손실 계산
                loss_dict = self.criterion(outputs, targets)
                loss = loss_dict['total_loss']
                
                # 통계 업데이트
                total_loss += loss.item()
                all_predictions.append(outputs['main_output'].cpu())
                all_targets.append(targets.cpu())
                
                pbar.set_postfix({'val_loss': f'{loss.item():.4f}'})
        
        # 에포크 메트릭 계산
        all_predictions = torch.cat(all_predictions, dim=0)
        all_targets = torch.cat(all_targets, dim=0)
        metrics = self.calculate_metrics(all_predictions, all_targets)
        
        avg_loss = total_loss / len(val_loader)
        return avg_loss, metrics
    
    def plot_training_history(self):
        """학습 기록 시각화"""
        if len(self.train_losses) == 0:
            return
            
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
        
        epochs = range(1, len(self.train_losses) + 1)
        
        # Loss plot
        ax1.plot(epochs, self.train_losses, 'b-', label='Train Loss')
        ax1.plot(epochs, self.val_losses, 'r-', label='Val Loss')
        ax1.set_title('Training and Validation Loss')
        ax1.set_xlabel('Epoch')
        ax1.set_ylabel('Loss')
        ax1.legend()
        ax1.grid(True)
        
        # MSE plot
        if self.train_metrics and self.val_metrics:
            train_mse = [m['mse_overall'] for m in self.train_metrics]
            val_mse = [m['mse_overall'] for m in self.val_metrics]
            
            ax2.plot(epochs, train_mse, 'b-', label='Train MSE')
            ax2.plot(epochs, val_mse, 'r-', label='Val MSE')
            ax2.set_title('MSE')
            ax2.set_xlabel('Epoch')
            ax2.set_ylabel('MSE')
            ax2.legend()
            ax2.grid(True)
            
            # R² plot
            train_r2 = [m['r2_overall'] for m in self.train_metrics]
            val_r2 = [m['r2_overall'] for m in self.val_metrics]
            
            ax3.plot(epochs, train_r2, 'b-', label='Train R²')
            ax3.plot(epochs, val_r2, 'r-', label='Val R²')
            ax3.set_title('R² Score')
            ax3.set_xlabel('Epoch')
            ax3.set_ylabel('R²')
            ax3.legend()
            ax3.grid(True)
            
            # Per-axis MSE (validation)
            axes_names = ['brightness', 'thickness', 'loudness', 'clarity']
            latest_val_mse = [self.val_metrics[-1][f'mse_{axis}'] for axis in axes_names]
            
            ax4.bar(axes_names, latest_val_mse)
            ax4.set_title('Latest Validation MSE per Axis')
            ax4.set_xlabel('Axis')
            ax4.set_ylabel('MSE')
            ax4.tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        plt.savefig(self.experiment_dir / 'training_history.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def train(self, train_loader: DataLoader, val_loader: DataLoader):
        """전체 학습 프로세스"""
        self.logger.info("학습 시작")
        self.logger.info(f"모델 파라미터 수: {sum(p.numel() for p in self.model.parameters()):,}")
        
        # 설정 저장
        self.save_config()
        
        for epoch in range(self.start_epoch, self.config.num_epochs):
            self.logger.info(f"Epoch {epoch+1}/{self.config.num_epochs}")
            
            # 학습
            train_loss, train_metrics = self.train_epoch(train_loader, epoch)
            
            # 검증
            val_loss, val_metrics = self.validate_epoch(val_loader, epoch)
            
            # 스케줄러 업데이트
            self.scheduler.step()
            
            # 메트릭 저장
            self.train_losses.append(train_loss)
            self.val_losses.append(val_loss)
            self.train_metrics.append(train_metrics)
            self.val_metrics.append(val_metrics)
            
            # TensorBoard 로깅
            self.writer.add_scalar('Epoch/Train_Loss', train_loss, epoch)
            self.writer.add_scalar('Epoch/Val_Loss', val_loss, epoch)
            self.writer.add_scalar('Epoch/Train_MSE', train_metrics['mse_overall'], epoch)
            self.writer.add_scalar('Epoch/Val_MSE', val_metrics['mse_overall'], epoch)
            self.writer.add_scalar('Epoch/Train_R2', train_metrics['r2_overall'], epoch)
            self.writer.add_scalar('Epoch/Val_R2', val_metrics['r2_overall'], epoch)
            
            # 개별 축 메트릭
            for axis in ['brightness', 'thickness', 'loudness', 'clarity']:
                self.writer.add_scalar(f'Val_MSE/{axis}', val_metrics[f'mse_{axis}'], epoch)
                self.writer.add_scalar(f'Val_R2/{axis}', val_metrics[f'r2_{axis}'], epoch)
            
            # 로깅
            self.logger.info(f"Train Loss: {train_loss:.4f}, Val Loss: {val_loss:.4f}")
            self.logger.info(f"Train R²: {train_metrics['r2_overall']:.4f}, Val R²: {val_metrics['r2_overall']:.4f}")
            
            # 체크포인트 저장
            is_best = val_loss < self.best_val_loss
            if is_best:
                self.best_val_loss = val_loss
                self.patience_counter = 0
            else:
                self.patience_counter += 1
            
            # 정기 체크포인트 저장
            if (epoch + 1) % 10 == 0:
                self.save_checkpoint(epoch, is_best)
            
            # Early stopping
            if self.patience_counter >= self.config.patience:
                self.logger.info(f"Early stopping at epoch {epoch+1}")
                break
            
            # 학습 기록 플롯 업데이트
            if (epoch + 1) % 5 == 0:
                self.plot_training_history()
        
        # 최종 체크포인트 저장
        self.save_checkpoint(epoch, is_best)
        self.plot_training_history()
        
        self.logger.info("학습 완료")
        self.writer.close()

def main():
    parser = argparse.ArgumentParser(description='SongLab 딥러닝 모델 학습')
    parser.add_argument('--experiment-name', type=str, default='vocal_analyzer_v1',
                       help='실험 이름')
    parser.add_argument('--resume', type=str, default=None,
                       help='체크포인트 경로 (학습 재개)')
    parser.add_argument('--data-dir', type=str, default='data/collected',
                       help='데이터 디렉토리')
    parser.add_argument('--batch-size', type=int, default=16,
                       help='배치 크기')
    parser.add_argument('--epochs', type=int, default=100,
                       help='에포크 수')
    parser.add_argument('--lr', type=float, default=1e-4,
                       help='학습률')
    
    args = parser.parse_args()
    
    # 설정
    config = VocalAnalyzerConfig()
    config.batch_size = args.batch_size
    config.num_epochs = args.epochs
    config.learning_rate = args.lr
    
    # 데이터 로드
    collector = DataCollector(args.data_dir)
    
    if collector.metadata['total_samples'] < 20:
        print(f"데이터 부족: {collector.metadata['total_samples']} 샘플")
        print("최소 20개 이상의 샘플이 필요합니다.")
        return
    
    train_dataset, val_dataset = collector.get_dataset(test_size=0.2)
    
    train_loader = DataLoader(
        train_dataset, 
        batch_size=config.batch_size, 
        shuffle=True,
        num_workers=4,
        pin_memory=True
    )
    
    val_loader = DataLoader(
        val_dataset, 
        batch_size=config.batch_size, 
        shuffle=False,
        num_workers=4,
        pin_memory=True
    )
    
    print(f"학습 데이터: {len(train_dataset)} 샘플")
    print(f"검증 데이터: {len(val_dataset)} 샘플")
    
    # 트레이너 초기화
    trainer = Trainer(config, args.experiment_name)
    
    # 체크포인트 로드 (선택사항)
    if args.resume:
        trainer.load_checkpoint(args.resume)
    
    # 학습 시작
    trainer.train(train_loader, val_loader)

if __name__ == "__main__":
    main()