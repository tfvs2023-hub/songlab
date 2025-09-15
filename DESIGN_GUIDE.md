# SongLab 디자인 가이드 (웹디자이너용)

## 🎨 프로젝트 개요
- **프레임워크**: React + TailwindCSS
- **스타일 방식**: Utility-first CSS (TailwindCSS 클래스)
- **컬러 테마**: Blue/Purple 그라데이션

## 📁 디자인 파일 구조

### 1. 메인 컴포넌트 위치
```
src/App.jsx - 모든 UI 컴포넌트가 여기 있습니다
```

## 🎨 주요 컬러 팔레트

### Primary Colors
- **Blue**: `#3B82F6` (blue-500)
- **Purple**: `#A855F7` (purple-500)
- **Yellow**: `#FCD34D` (yellow-300)

### Background Gradients
```css
/* 메인 배경 */
background: linear-gradient(to bottom right, #EFF6FF, #FFFFFF, #FAF5FF);
/* from-blue-50 via-white to-purple-50 */

/* 랜딩 페이지 배경 */
background: linear-gradient(135deg, #667EEA 0%, #764BA2 100%);
```

### Status Colors
- **Success**: `#10B981` (green-500)
- **Warning**: `#F59E0B` (amber-500)
- **Error**: `#EF4444` (red-500)
- **Info**: `#3B82F6` (blue-500)

## 📐 레이아웃 구조

### 1. 랜딩 페이지 (Landing Page)
```css
.landing-container {
  min-height: 100vh;
  background: linear-gradient(135deg, #667EEA 0%, #764BA2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
}

.hero-card {
  background: white;
  border-radius: 1.5rem;
  padding: 3rem;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
  max-width: 42rem;
}
```

### 2. 녹음 페이지 (Recording Page)
```css
.recording-page {
  min-height: 100vh;
  background: linear-gradient(to bottom right, #EFF6FF, #FFFFFF, #FAF5FF);
  padding: 1rem;
}

.recording-button {
  width: 8rem;
  height: 8rem;
  border-radius: 50%;
  border: 4px solid;
  transition: all 0.3s;
}

.recording-active {
  border-color: #EF4444; /* red-500 */
  background: #FEE2E2; /* red-100 */
  box-shadow: 0 10px 25px -5px rgba(239, 68, 68, 0.3);
}
```

### 3. 결과 페이지 (Results Page)
```css
.results-container {
  background: white;
  border-radius: 0.75rem;
  padding: 1.5rem;
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
}

.score-card {
  background: linear-gradient(to right, #3B82F6, #A855F7);
  color: white;
  padding: 1.5rem;
  border-radius: 0.5rem;
}
```

## 🎯 주요 컴포넌트 스타일

### 버튼 스타일
```css
/* Primary Button */
.btn-primary {
  background: #3B82F6;
  color: white;
  padding: 0.75rem 2rem;
  border-radius: 0.75rem;
  font-weight: 600;
  transition: all 0.3s;
}

.btn-primary:hover {
  background: #2563EB;
  transform: scale(1.05);
}

/* Secondary Button */
.btn-secondary {
  background: #F3F4F6;
  color: #374151;
  padding: 0.75rem 1.5rem;
  border-radius: 0.75rem;
  transition: all 0.2s;
}
```

### 카드 스타일
```css
.card {
  background: white;
  border-radius: 0.75rem;
  padding: 1.5rem;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  border: 1px solid #E5E7EB;
}

.card-hover:hover {
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}
```

### 애니메이션
```css
/* Pulse Animation (녹음 중) */
@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

.animate-pulse {
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

/* Bounce Animation (버튼) */
@keyframes bounce {
  0%, 100% {
    transform: translateY(-25%);
    animation-timing-function: cubic-bezier(0.8, 0, 1, 1);
  }
  50% {
    transform: translateY(0);
    animation-timing-function: cubic-bezier(0, 0, 0.2, 1);
  }
}
```

## 📱 반응형 디자인

### Breakpoints
- **sm**: 640px
- **md**: 768px
- **lg**: 1024px
- **xl**: 1280px

### 반응형 그리드
```css
/* 모바일 */
.grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1rem;
}

/* 태블릿 이상 */
@media (min-width: 768px) {
  .grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

/* 데스크톱 */
@media (min-width: 1024px) {
  .grid {
    grid-template-columns: repeat(3, 1fr);
  }
}
```

## 🎨 특수 효과

### 그라데이션 텍스트
```css
.gradient-text {
  background: linear-gradient(to right, #3B82F6, #A855F7);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
```

### 글래스모피즘
```css
.glass {
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.3);
}
```

## 🔤 타이포그래피

### 폰트 크기
- **제목**: `text-3xl` (1.875rem)
- **부제목**: `text-xl` (1.25rem)
- **본문**: `text-base` (1rem)
- **작은 텍스트**: `text-sm` (0.875rem)
- **극소 텍스트**: `text-xs` (0.75rem)

### 폰트 굵기
- **bold**: `font-bold` (700)
- **semibold**: `font-semibold` (600)
- **medium**: `font-medium` (500)
- **normal**: `font-normal` (400)

## 💡 디자인 개선 제안 환영!

이 파일을 참고하여 디자인을 검토하시고, 개선사항이 있으면 알려주세요.
특히 다음 부분들에 대한 피드백을 환영합니다:
- 색상 조합
- 레이아웃 구조
- 애니메이션 효과
- 반응형 디자인
- 접근성 개선