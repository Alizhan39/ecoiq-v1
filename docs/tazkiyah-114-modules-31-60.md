# Tazkiyah 114 — Modules 31–60

> Structured product concepts for modules 31–60. Each module is a *lens* onto the
> [Repair Engine](tazkiyah-114-transformation-operating-system.md#c-repair-engine).
>
> **All content is reflection inspired by Qur'anic themes — pending scholar review.** Nothing
> here is tafsir, fatwa, therapy, or diagnosis. Dua lines are **prompts**, not narrated duas
> unless explicitly sourced. Sensitive modules require scholar **and** wellbeing review. See
> [safety principles](tazkiyah-114-safety-principles.md).
>
> Seed data for these modules: `content/tazkiyah114/moduleSeeds.ts`.

---

## 31. Heart Diseases Library

**Purpose:** A calm, browsable library of diseases of the heart (e.g. envy, pride, despair,
ostentation) with reflection and repair — a diagnostic starting point, not a label.

**User problems:**
- "Something is off in my heart and I can't name it."
- "I keep reacting badly and don't understand why."

**Core experience:**
- Browse or take a gentle self-reflection to surface a likely disease.
- Each disease links to its opposite virtue (Module 32) and a Surah pathway.

**Content blocks:**
- How it shows up · what it quietly destroys · Qur'anic reminder · opposite virtue · one repair action · 7-day practice.

**Safety notes:**
- A reflection, not a diagnosis; persistent distress deserves professional support.

**Future implementation:**
- Route: `/tazkiyah/heart-diseases` and `/tazkiyah/heart-diseases/[slug]`
- Data: `HeartDisease { slug, name, showsUp[], destroys, reminderTheme, oppositeVirtueSlug, action, sevenDay[] }`
- Component: `DiseaseLibraryGrid`, `DiseaseCard`, `VirtueLink`

---

## 32. Virtue Builder

**Purpose:** Build a target virtue (sabr, shukr, tawakkul, ikhlas, hayaa, rahmah…) through small daily training.

**User problems:**
- "I want to become more patient/grateful/sincere but don't know how."

**Core experience:**
- Pick a virtue → see its opposite disease, Qur'anic anchors, daily practice, self-checks, 7-day exercise.

**Content blocks:**
- Meaning · opposite disease · Qur'anic theme · daily practice · self-check questions · 7-day training.

**Safety notes:**
- Frame as gradual growth, never spiritual perfectionism or self-shame.

**Future implementation:**
- Route: `/tazkiyah/virtues/[slug]`
- Data: `Virtue { slug, name, oppositeDisease, themes[], dailyPractice, selfChecks[], sevenDay[] }`
- Component: `VirtueTrainer`, `SelfCheckList`, `SevenDayPlan`

---

## 33. My Current Test

**Purpose:** Help a user name the test they are *in right now* and find Qur'anic companionship for it.

**User problems:**
- "I'm going through something and don't know how to hold it with faith."

**Core experience:**
- A few gentle questions → a named "current test" → pathway, reflection, dua prompt, one step.

**Content blocks:**
- Naming the test · what Allah may be inviting · ayah reflection · one action · dua prompt.

**Safety notes:**
- Never imply the test is punishment or that the user "deserved" it; avoid toxic positivity.

**Future implementation:**
- Route: `/tazkiyah/my-current-test`
- Data: reuses `Pathway`; adds `testType` tag.
- Component: `GentleStepper`, `PathwayResult`

---

## 34. Qur'anic Stories as Life Mirrors

**Purpose:** Use Qur'anic narratives as mirrors for present struggles (patience, betrayal, fear, exile, hope).

**User problems:**
- "I feel alone in this — has anyone been through something like it?"

**Core experience:**
- Browse stories tagged by the human experience they mirror; each links to a pathway and action.

**Content blocks:**
- The human experience mirrored · gentle retelling theme · ayah anchors · reflection · one action.

**Safety notes:**
- Retell themes humbly; avoid embellishment or unsourced detail; mark needs-review.

**Future implementation:**
- Route: `/tazkiyah/stories` and `/tazkiyah/stories/[slug]`
- Data: `StoryMirror { slug, title, mirrors[], themeText, ayahRefs[], pathwaySlug }`
- Component: `StoryMirrorCard`, `MirrorTagFilter`

---

## 35. Prophet Yusuf Pathway

**Purpose:** A flagship multi-stage pathway through Surah Yusuf — betrayal, patience, prison, restraint, reunion.

**User problems:**
- "I've been betrayed / wronged / stuck in an unfair season."

**Core experience:**
- A staged journey (the pit → the test → the prison → the rise → forgiveness), each stage with reflection, action, dua prompt.

**Content blocks:**
- Stage theme · ayah anchors (e.g. 12:87, 12:90) · reflection question · one action · dua prompt.

**Safety notes:**
- Patience is not passivity; betrayal recovery may need real-world support and boundaries.

**Future implementation:**
- Route: `/tazkiyah/pathways/yusuf`
- Data: `StagedPathway { slug, stages: [{ theme, ayahRefs[], question, action, duaPrompt }] }`
- Component: `StagedPathway`, `StageProgress`

---

## 36. Du'a Builder

**Purpose:** Help a user shape their own honest du'a in their own words, anchored to a need.

**User problems:**
- "I don't know what to say to Allah." / "My du'a feels empty."

**Core experience:**
- Choose a need → guided prompts (praise → confess → ask → trust) → the user writes their own du'a.

**Content blocks:**
- Du'a *prompts* and a structure to follow — **not** presented as narrated/authentic du'as.

**Safety notes:**
- **Critical:** generated lines are prompts, not Sunnah/narrated du'as. Authentic narrated du'as
  must be sourced and clearly labelled separately.

**Future implementation:**
- Route: `/tazkiyah/dua-builder`
- Data: `DuaPromptSet { needSlug, structure[], promptLines[] }`; separate `NarratedDua { source }`.
- Component: `DuaBuilderWizard`, `DuaPromptCard`

---

## 37. Istikhara + Decision Journal

**Purpose:** Support sincere decision-making with istikhara and structured reflection (non-fatwa).

**User problems:**
- "I have a big decision and I'm scared/confused."

**Core experience:**
- Reflection questions (halal? taqwa? harm? motive? counsel? istikhara?) + a decision journal over time.

**Content blocks:**
- Reflection scaffold · istikhara reminder · decision journal entries · revisit prompt.

**Safety notes:**
- **Istikhara is not reduced to dreams.** It is a prayer for guidance; outcomes unfold through
  circumstances and sound counsel. No fatwa; route ruling questions to scholars.

**Future implementation:**
- Route: `/tazkiyah/decision-compass`
- Data: `Decision { question, reflections{}, istikharaMade, counselSought, journal[] }`
- Component: `DecisionCompass`, `DecisionJournal`

---

## 38. Repentance Room

**Purpose:** A gentle pathway for people drowning in guilt who want to return to Allah.

**User problems:**
- "I sinned, I feel ashamed, and I fear I cannot come back."

**Core experience:**
- A soft stepper: name without despair → remember mercy → tawbah → block one trigger → replace with a good deed → track one day of return.

**Content blocks:**
- "Do not let shame become distance." · "Return immediately." · "Change one condition." · "Do one good deed after it."

**Safety notes:**
- **Sensitive.** Never frame relapse as proof of worthlessness. If compulsive/addictive, route to
  professional help. Avoid religious shame.

**Future implementation:**
- Route: `/tazkiyah/repentance-room`
- Data: `TawbahSession { trigger, lie, boundary, replacement, dayTracked }`
- Component: `GentleStepper`, `DuaPromptCard`, `TriggerBlocker`, `TawbahTracker`

---

## 39. Salah Repair Pathway

**Purpose:** Help users rebuild a consistent, present prayer life — without shame.

**User problems:**
- "I keep missing salah." / "I pray but my heart isn't in it."

**Core experience:**
- Diagnose the gap (consistency vs presence) → one small fix → track prayers gently for 7 days.

**Content blocks:**
- The barrier · one tiny next step · presence tips · ayah reflection · tracker.

**Safety notes:**
- No guilt-tripping; meet the user where they are; small wins first.

**Future implementation:**
- Route: `/tazkiyah/salah-repair`
- Data: `SalahPlan { barrier, microStep, tracker[7] }`
- Component: `SalahTracker`, `GentleStepper`

---

## 40. Digital Nafs / Social Media Repair

**Purpose:** Repair the relationship with the phone — comparison, validation-seeking, wasted time.

**User problems:**
- "I scroll for hours and feel worse." / "I compare myself constantly."

**Core experience:**
- Name the digital trigger → one boundary (a screen-free window, a muted feed) → a halal replacement → 7-day track.

**Content blocks:**
- The whisper vs the truth · one boundary · one replacement · reflection · tracker.

**Safety notes:**
- Addiction-adjacent; if compulsive, suggest professional support. Avoid shame.

**Future implementation:**
- Route: `/tazkiyah/digital-nafs`
- Data: `DigitalPlan { trigger, boundary, replacement, tracker[7] }`
- Component: `TriggerBlocker`, `HabitTracker`

---

## 41. Marriage and Family Repair

**Purpose:** Reflection pathways for tension, distance, and patience in marriage and family.

**User problems:**
- "There's constant conflict / coldness / resentment at home."

**Core experience:**
- What Allah asks here · what boundary is allowed · what character I need · one action today · one dua prompt.

**Content blocks:**
- Character before reaction · the allowed boundary · one repair action · dua prompt.

**Safety notes:**
- **Sensitive.** Qur'anic patience is **never** acceptance of abuse. Always show boundaries and a
  safety/escalation path; route to qualified counsel and, where there is harm, to protection
  services.

**Future implementation:**
- Route: `/tazkiyah/relationships/marriage-family`
- Data: `RelationshipPathway { context, allowedBoundary, virtue, action, duaPrompt, safetyNote }`
- Component: `RelationshipPathway`, `BoundaryCard`, `SafetyBanner`

---

## 42. Motherhood / Fatherhood Tazkiyah

**Purpose:** Support parents in raising character while repairing their own hearts.

**User problems:**
- "I lose my temper with my kids." / "I feel guilty as a parent."

**Core experience:**
- A weekly character theme for the family + a self-repair reflection for the parent.

**Content blocks:**
- Parent self-check · child character theme · one family action · dua prompt.

**Safety notes:**
- Parenting guilt is common; frame gently, avoid perfectionism; not clinical advice.

**Future implementation:**
- Route: `/tazkiyah/parenting`
- Data: `ParentingTheme { theme, parentCheck[], childAction, familyAction, duaPrompt }`
- Component: `FamilyThemeCard`, `ParentSelfCheck`

---

## 43. Grief and Loss Pathway

**Purpose:** Qur'anic companionship in bereavement and loss — without rushing the pain.

**User problems:**
- "I lost someone/something and I can't carry it."

**Core experience:**
- Very gentle pacing: acknowledge → hold a verse → a small step → dua prompt → permission to grieve.

**Content blocks:**
- "You are allowed to grieve." · an anchor verse · one tiny step · dua prompt · "you are not alone."

**Safety notes:**
- **Sensitive.** No promises of instant relief; no implication of punishment. Route to grief
  support and professionals; this is companionship, not therapy.

**Future implementation:**
- Route: `/tazkiyah/grief`
- Data: `GriefPathway { stageText, anchorAyahRef, smallStep, duaPrompt, supportRouting }`
- Component: `GentlePacing`, `SupportBanner`

---

## 44. Anger Repair Pathway

**Purpose:** Move from reactive anger to restraint (hilm) and mercy.

**User problems:**
- "I explode and regret it." / "My anger hurts people I love."

**Core experience:**
- Spot the trigger → the pause practice → the prophetic restraint model → one repair action → 7-day track.

**Content blocks:**
- Trigger map · the pause · restraint as strength · one repair · dua prompt.

**Safety notes:**
- If anger involves harm to others or self, route to professional support; safety first.

**Future implementation:**
- Route: `/tazkiyah/anger-repair`
- Data: `AngerPlan { trigger, pausePractice, repairAction, tracker[7] }`
- Component: `PausePractice`, `HabitTracker`

---

## 45. Envy Repair Pathway

**Purpose:** From envy (hasad) to contentment (qana'ah) and wanting good for others.

**User problems:**
- "I feel diminished by other people's blessings."

**Core experience:**
- Catch the comparison → reframe through provision-themes → make dua for the person → gratitude practice.

**Content blocks:**
- Comparison vs trust · refuge from envy · praise/dua for the other · gratitude action.

**Safety notes:**
- Reflection on character, not therapy; persistent distress deserves support.

**Future implementation:**
- Route: `/tazkiyah/envy-repair`
- Data: reuses `Pathway` with `oppositeVirtue: "contentment"`.
- Component: `ReframeCard`, `GratitudeTracker`

---

## 46. Money Without Losing Your Soul

**Purpose:** Pursue rizq and ambition without riba, corruption, arrogance, or fear-driven shortcuts.

**User problems:**
- "I'm scared about money and tempted to compromise my deen."

**Core experience:**
- Reframe wall (money without fear, rizq without riba, ambition with tawakkul) → one halal action → tracker.

**Content blocks:**
- Effort as worship · tawakkul ≠ laziness · halal boundary · one action · dua prompt.

**Safety notes:**
- **Sensitive.** Real debt/financial crisis → seek qualified financial + scholarly advice; never
  promise financial return from worship.

**Future implementation:**
- Route: `/tazkiyah/money`
- Data: reuses rizq `Pathway`; links to ethical-wealth/Maqasid content.
- Component: `ReframeWall`, `DoDontCard`

---

## 47. Qur'an and Emotional States

**Purpose:** A fast index from an emotion to Qur'anic companionship (anxiety, sadness, fear, anger, numbness, hope).

**User problems:**
- "I just need something for how I feel right now."

**Core experience:**
- Pick an emotion → one verse to hold → one reflection → one action → dua prompt.

**Content blocks:**
- Emotion → anchor verse → reflection → action → dua prompt.

**Safety notes:**
- Not a mood diagnosis; crisis states route to Life Crisis Mode and professional help.

**Future implementation:**
- Route: `/tazkiyah/emotions/[state]`
- Data: `EmotionEntry { state, anchorAyahRef, reflection, action, duaPrompt }`
- Component: `EmotionPicker`, `AnchorVerseCard`

---

## 48. My Allah Assumption (Husn al-Dhann)

**Purpose:** Examine and repair one's assumption about Allah — from fear/distance to good expectation.

**User problems:**
- "I feel like Allah is angry with me / has forgotten me."

**Core experience:**
- Name the assumption → reflect on Allah's mercy and nearness → one practice of good expectation.

**Content blocks:**
- The assumption · Qur'anic reminder of mercy/nearness · reflection · one practice · dua prompt.

**Safety notes:**
- Handle despair gently; avoid both false guilt and toxic positivity.

**Future implementation:**
- Route: `/tazkiyah/allah-assumption`
- Data: `AssumptionEntry { assumption, reminderTheme, practice, duaPrompt }`
- Component: `AssumptionReframe`

---

## 49. From Reaction to Revelation

**Purpose:** Train the pause between impulse and action — responding from values, not reactivity.

**User problems:**
- "I react instantly and regret it."

**Core experience:**
- Catch the impulse → pause → recall a relevant theme → choose the response → reflect.

**Content blocks:**
- The trigger · the pause · the chosen response · reflection · dua prompt.

**Safety notes:**
- General self-regulation reflection; not clinical impulse-control treatment.

**Future implementation:**
- Route: `/tazkiyah/reaction-to-revelation`
- Data: `PausePlan { impulse, pausePractice, chosenResponse }`
- Component: `PausePractice`

---

## 50. Daily Mizan

**Purpose:** The daily morning + evening reflection practice (the "balance").

**User problems:**
- "I drift through days without intention or reflection."

**Core experience:**
- Morning: intention · weakness to guard · Name of Allah · one action. Evening: muhasabah questions.

**Content blocks:**
- Morning set · evening muhasabah set · private journal capture.

**Safety notes:**
- Muhasabah, framed gently — never spiritual scorekeeping or shame.

**Future implementation:**
- Route: `/tazkiyah/daily-mizan`
- Data: `MizanDay { date, morning{}, evening{} }`
- Component: `MorningMizan`, `EveningMuhasabah`

---

## 51. Qur'anic Boundaries

**Purpose:** Reflection on healthy boundaries grounded in justice, dignity, and mercy.

**User problems:**
- "People keep crossing my limits and I feel guilty saying no."

**Core experience:**
- Clarify the boundary → why it is allowed → how to hold it with character → one action.

**Content blocks:**
- The allowed boundary · justice vs harm · holding it with ihsan · one action · dua prompt.

**Safety notes:**
- **Sensitive.** Sabr is not silence against injustice; forgiveness does not mean returning to
  harm. Route abuse situations to qualified counsel/protection.

**Future implementation:**
- Route: `/tazkiyah/boundaries`
- Data: `BoundaryPathway { situation, allowedBoundary, character, action, safetyNote }`
- Component: `BoundaryCard`, `SafetyBanner`

---

## 52. Amanah of the Body

**Purpose:** Treating the body as a trust — rest, health, gratitude, modesty (non-medical).

**User problems:**
- "I neglect/abuse my body." / "I feel shame about my body."

**Core experience:**
- One small act of care today, framed as honouring an amanah; gratitude for health.

**Content blocks:**
- Body as trust · one care action · gratitude practice · dua prompt.

**Safety notes:**
- **Sensitive.** Not medical advice; eating-disorder / self-harm content routes to professionals.
  Avoid body shame.

**Future implementation:**
- Route: `/tazkiyah/amanah/body`
- Data: reuses `AmanahPathway`.
- Component: `AmanahCard`, `SupportBanner`

---

## 53. Amanah of Time

**Purpose:** Time as a trust — barakah, presence, and intentional use.

**User problems:**
- "My time leaks away and I have nothing to show Allah."

**Core experience:**
- Audit one hour → redirect it to faith/good/loved ones → track.

**Content blocks:**
- Time as trust · one redirected hour · reflection · dua prompt.

**Safety notes:**
- Encourage barakah, not burnout or productivity guilt.

**Future implementation:**
- Route: `/tazkiyah/amanah/time`
- Data: `AmanahPathway { domain: "time", action, reflection, duaPrompt }`
- Component: `AmanahCard`, `HourAudit`

---

## 54. Amanah of Speech

**Purpose:** The tongue as a trust — truthfulness, gentleness, restraint, no backbiting.

**User problems:**
- "I gossip / lie / speak harshly / complain constantly."

**Core experience:**
- Pick one speech habit → one restraint or repair → reflect → track.

**Content blocks:**
- Speech as trust · one restraint · one repair (e.g. retract a gossip) · dua prompt.

**Safety notes:**
- Reflection on character; avoid self-shame; encourage gradual change.

**Future implementation:**
- Route: `/tazkiyah/amanah/speech`
- Data: `AmanahPathway { domain: "speech", habit, restraint, repair }`
- Component: `AmanahCard`, `HabitTracker`

---

## 55. Amanah of Wealth

**Purpose:** Wealth as a trust — halal earning, zakah/sadaqah, no riba, generosity without showing off.

**User problems:**
- "How do I hold money without it holding me?"

**Core experience:**
- One act of ethical generosity or halal correction → reflect → track.

**Content blocks:**
- Wealth as trust · giving without riya · halal boundary · one action · dua prompt.

**Safety notes:**
- Not financial/legal advice; riba/contract questions go to scholars and qualified advisers.

**Future implementation:**
- Route: `/tazkiyah/amanah/wealth`
- Data: `AmanahPathway { domain: "wealth", action, reflection }`
- Component: `AmanahCard`, `DoDontCard`

---

## 56. Amanah of Power

**Purpose:** Authority and influence as a trust — justice, humility, shura, no corruption.

**User problems:**
- "I have authority and fear arrogance/corruption." (managers, leaders, parents)

**Core experience:**
- One leadership self-check → one just/humble action → reflect.

**Content blocks:**
- Power as trust · justice & humility · shura · one action · dua prompt.

**Safety notes:**
- Connects to Founder/Leader mode; not governance/legal advice.

**Future implementation:**
- Route: `/tazkiyah/amanah/power`
- Data: `AmanahPathway { domain: "power", action, selfCheck[] }`
- Component: `AmanahCard`, `LeaderSelfCheck`

---

## 57. The 4 Return Paths

**Purpose:** Four gentle on-ramps back to Allah after distance (through mercy, fear, love, gratitude).

**User problems:**
- "I want to return but don't know where to start."

**Core experience:**
- Choose the doorway that fits today → a verse, a reflection, one step home.

**Content blocks:**
- The four doorways · an anchor verse each · one step · dua prompt.

**Safety notes:**
- Avoid shame; every return is presented as accepted and enough to begin.

**Future implementation:**
- Route: `/tazkiyah/return-paths`
- Data: `ReturnPath { doorway, anchorAyahRef, step, duaPrompt }`
- Component: `ReturnDoorways`

---

## 58. Repair by Time of Day

**Purpose:** Match a short repair practice to the moment — fajr, midday, asr slump, maghrib, before sleep.

**User problems:**
- "I want a tiny practice that fits the moment I'm in."

**Core experience:**
- Detect/choose time of day → one verse, one micro-action, one dua prompt for that window.

**Content blocks:**
- Time-window theme · micro-action · dua prompt.

**Safety notes:**
- Light, optional, never guilt-based; respects the user's schedule.

**Future implementation:**
- Route: `/tazkiyah/by-time`
- Data: `TimeWindow { window, theme, microAction, duaPrompt }`
- Component: `TimeOfDayCard`

---

## 59. Ramadan / Dhul Hijjah / Friday Modes

**Purpose:** Seasonal "modes" that reshape the daily companion for blessed times.

**User problems:**
- "I want to make the most of Ramadan / the 10 days / Jumu'ah."

**Core experience:**
- A seasonal mode toggles themed daily practices, reflections, and gentle goals.

**Content blocks:**
- Seasonal theme · daily focus · reflection · dua prompt (sourced du'as labelled separately).

**Safety notes:**
- Encourage sincerity over performance; avoid worship-comparison and burnout.

**Future implementation:**
- Route: `/tazkiyah/modes/[season]`
- Data: `SeasonMode { season, dailyThemes[], reflection }`
- Component: `SeasonModeBanner`, `SeasonDayCard`

---

## 60. Community Circles

**Purpose:** Small, safe, purpose-led circles (family, sisters, youth, founders, grief) — not a feed.

**User problems:**
- "I want support and accountability without social-media toxicity."

**Core experience:**
- Join a small circle → shared 7-day challenge → anonymous reflections → "I benefited from this".

**Content blocks:**
- Circle purpose · shared challenge · accountability prompts · no public metrics.

**Safety notes:**
- **Sensitive (community).** Moderation + wellbeing escalation required; no vanity metrics, no
  follower counts, no public worship ranking, no infinite scroll. Grief/abuse circles need
  trained moderation.

**Future implementation:**
- Route: `/tazkiyah/circles` and `/tazkiyah/circles/[id]`
- Data: `Circle { id, type, members[], challenge, reflections[] }` (privacy-first)
- Component: `CircleRoom`, `GroupChallenge`, `BenefitedButton`

---

*Last updated: 2026-06-19. Modules 1–30 are covered in the
[architecture brief](tazkiyah-114-architecture.md) and the
[transformation OS](tazkiyah-114-transformation-operating-system.md).*
