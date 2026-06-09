import React from 'react';
import { Composition } from 'remotion';
import { CountryTransitionBrief, countryDefaults } from './compositions/CountryTransitionBrief';
import { CompanyEsgRiskBrief, companyDefaults } from './compositions/CompanyEsgRiskBrief';
import { KhalifaToursImpactExplainer, toursDefaults } from './compositions/KhalifaToursImpactExplainer';

// 1080p, 30fps, ~6s briefs. Data flows in via defaultProps → override with
// `--props='{...}'` at render time (the "report-to-video" workflow).
export const RemotionRoot: React.FC = () => (
  <>
    <Composition
      id="CountryTransitionBrief"
      component={CountryTransitionBrief}
      durationInFrames={180}
      fps={30}
      width={1920}
      height={1080}
      defaultProps={countryDefaults}
    />
    <Composition
      id="CompanyEsgRiskBrief"
      component={CompanyEsgRiskBrief}
      durationInFrames={180}
      fps={30}
      width={1920}
      height={1080}
      defaultProps={companyDefaults}
    />
    <Composition
      id="KhalifaToursImpactExplainer"
      component={KhalifaToursImpactExplainer}
      durationInFrames={190}
      fps={30}
      width={1920}
      height={1080}
      defaultProps={toursDefaults}
    />
  </>
);
