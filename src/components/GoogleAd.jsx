import React, { useEffect, useRef } from 'react';

const GoogleAd = ({ slot, format = 'auto', responsive = true }) => {
  const adRef = useRef(null);
  const isAdLoaded = useRef(false);

  useEffect(() => {
    // 이미 광고가 로드되었거나 adRef가 없으면 실행하지 않음
    if (isAdLoaded.current || !adRef.current) return;

    try {
      // AdSense 스크립트가 로드되었는지 확인
      if (window.adsbygoogle && adRef.current) {
        // 이미 광고가 있는지 확인
        const existingAd = adRef.current.querySelector('.adsbygoogle');
        if (!existingAd || existingAd.getAttribute('data-adsbygoogle-status') !== 'done') {
          (window.adsbygoogle = window.adsbygoogle || []).push({});
          isAdLoaded.current = true;
        }
      }
    } catch (err) {
      console.error('AdSense error:', err);
    }
  }, [slot]);

  // 컴포넌트 언마운트 시 상태 리셋
  useEffect(() => {
    return () => {
      isAdLoaded.current = false;
    };
  }, []);

  return (
    <div ref={adRef}>
      <ins
        className="adsbygoogle"
        style={{ display: 'block' }}
        data-ad-client="ca-pub-6705069504882755"
        data-ad-slot={slot}
        data-ad-format={format}
        data-full-width-responsive={responsive}
      />
    </div>
  );
};

export default GoogleAd;