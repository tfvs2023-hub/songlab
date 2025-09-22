import React, { useState, useEffect } from 'react';
import { Upload, Sparkles } from 'lucide-react';

const FALLBACK_SVG = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='480' height='360'><rect width='100%25' height='100%25' fill='%23dddddd'/><text x='50%25' y='50%25' dominant-baseline='middle' text-anchor='middle' font-family='Arial, Helvetica, sans-serif' font-size='18' fill='%23666'>YouTube Search</text></svg>";

export default function VocalAnalysisPlatform() {
  const [currentStep, setCurrentStep] = useState('landing');
  const [audioFile, setAudioFile] = useState(null);
  const [analysisResults, setAnalysisResults] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const API_URL = (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_API_URL && import.meta.env.VITE_API_URL.trim()) || (typeof window !== 'undefined' && window.location.origin) || '';

  useEffect(() => {
    let mounted = true;
    (async () => {
      try { await fetch(`${API_URL}/api/health`); } catch (e) { /* ignore */ }
      if (!mounted) return;
    })();
    return () => { mounted = false; };
  }, [API_URL]);

  const handleFileUpload = (e) => {
    const f = e.target.files && e.target.files[0];
    if (!f) return;
    if (f.type.startsWith('audio/') || f.name.endsWith('.m4a')) setAudioFile(f);
    else alert('음성 파일만 업로드 가능합니다.');
  };

  const analyzeAudioFile = async (file) => {
    setIsAnalyzing(true);
    try {
      const fd = new FormData();
      fd.append('file', file);
      const res = await fetch(`${API_URL}/api/analyze?force_engine=studio`, { method: 'POST', body: fd });
      if (!res.ok) throw new Error('backend error');
      return await res.json();
    } catch (err) {
      return { mbti: { typeName: '데모 타입' }, youtube_videos: [] };
    } finally { setIsAnalyzing(false); }
  };

  const startAnalysis = async () => {
    if (!audioFile) return;
    setCurrentStep('analysis');
    const res = await analyzeAudioFile(audioFile);
    setAnalysisResults(res);
    setCurrentStep('results');
  };

  return (
    <div>
      {currentStep === 'landing' && (
        <div className="min-h-screen flex items-center justify-center">
          <div className="text-center p-8">
            <Sparkles className="w-16 h-16 mx-auto mb-4" />
            <h1 className="text-3xl font-bold mb-4">SongLab</h1>
            <button onClick={() => setCurrentStep('record')} className="px-6 py-3 bg-indigo-600 text-white rounded-lg">무료로 테스트해보기</button>
          </div>
        </div>
      )}

      {currentStep === 'record' && (
        <div className="min-h-screen p-8">
          <div className="max-w-2xl mx-auto bg-white p-6 rounded-lg shadow">
            <h2 className="text-xl font-semibold mb-4">녹음 또는 파일 업로드</h2>
            <div className="mb-4">
              <label className="inline-flex items-center gap-2 bg-gray-100 px-4 py-2 rounded cursor-pointer">
                <Upload className="w-5 h-5" /> 파일 업로드
                <input type="file" accept="audio/*,.m4a" onChange={handleFileUpload} className="hidden" />
              </label>
            </div>
            {audioFile && <div className="mb-4">선택된 파일: {audioFile.name}</div>}
            <div className="flex gap-3">
              <button onClick={startAnalysis} disabled={isAnalyzing || !audioFile} className="px-4 py-2 bg-blue-600 text-white rounded">{isAnalyzing ? '분석중...' : 'AI로 분석 시작'}</button>
              <button onClick={() => { setAudioFile(null); setCurrentStep('landing'); }} className="px-4 py-2 border rounded">취소</button>
            </div>
          </div>
        </div>
      )}

      {currentStep === 'analysis' && (
        <div className="min-h-screen flex items-center justify-center">분석중...</div>
      )}

      {currentStep === 'results' && (
        <div className="min-h-screen p-8">
          <div className="max-w-4xl mx-auto">
            <h2 className="text-2xl font-bold mb-4">분석 결과</h2>
            <div className="mb-4">타입: {analysisResults?.mbti?.typeName}</div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {(analysisResults?.youtube_videos || []).length > 0 ? (analysisResults.youtube_videos.map((v, i) => (
                <div key={i} className="p-3 border rounded">
                  <img src={v.thumbnail || `https://i.ytimg.com/vi/${v.videoId}/hqdefault.jpg`} alt={v.title} className="w-full h-32 object-cover mb-2" onError={(e) => { e.currentTarget.onerror = null; e.currentTarget.src = FALLBACK_SVG; }} />
                  <div className="font-medium">{v.title}</div>
                  <div className="text-xs text-gray-500">{v.channelTitle}</div>
                </div>
              ))) : (
                <div className="text-gray-500">추천 영상이 없습니다.</div>
              )}
            </div>
            <div className="mt-6">
              <button onClick={() => { setCurrentStep('record'); setAnalysisResults(null); setAudioFile(null); }} className="px-4 py-2 bg-purple-600 text-white rounded">다시 분석하기</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
