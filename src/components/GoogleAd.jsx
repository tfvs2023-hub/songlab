import React, { useEffect } from 'react';

const GoogleAd = ({ slot, format = 'auto', responsive = true }) => {
  useEffect(() => {
    try {
      // AdSense 스크립트가 로드되었는지 확인
      if (window.adsbygoogle) {
        (window.adsbygoogle = window.adsbygoogle || []).push({});
      }
    } catch (err) {
      console.error('AdSense error:', err);
    }
  }, []);

  return (
    <ins
      className="adsbygoogle"
      style={{ display: 'block' }}
      data-ad-client="ca-pub-6705069504882755"
      data-ad-slot={slot}
      data-ad-format={format}
      data-full-width-responsive={responsive}
    />
  );
};

export default GoogleAd;