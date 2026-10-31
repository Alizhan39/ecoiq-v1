import { useState } from 'react';
import { getLibraries, getScene, type Language } from '@/api/interactive';
import { useApi } from '@/hooks/useApi';
import { ErrorState, Loading } from '@/components/States';
import { ModelScene } from '@/features/interactive/ModelScene';
import './InteractiveLab.css';

const COPY = {
  en: { title: 'Interactive 3D and AR', demo: 'Experimental demonstration',
    note: 'Original illustrative geometry. No measured asset data or verified findings.',
    select: 'Explore a part', empty: 'No measurement or supporting evidence has been recorded.',
    load: 'Load 3D model', loading: 'Loading 3D model…', ar: 'View in your space',
    fallback: 'AR requires HTTPS and a compatible device. You can still explore the parts below.',
    error: 'The 3D or AR view could not start. Use the text view or try loading again.',
    alt: 'Three illustrative blocks for energy, water and materials',
    libraries: 'Integration library catalogue', ui: 'Interactive interface', xr: 'AR and 3D',
    installed: 'Integrated', option: 'Option', language: 'Language' },
  ru: { title: 'Интерактивный 3D и AR', demo: 'Экспериментальная демонстрация',
    note: 'Иллюстративная геометрия. Измерений реального объекта и подтверждённых выводов нет.',
    select: 'Выберите элемент', empty: 'Измерения и подтверждающие источники пока не добавлены.',
    load: 'Загрузить 3D-модель', loading: 'Загрузка 3D-модели…', ar: 'Посмотреть в своём пространстве',
    fallback: 'Для AR нужны HTTPS и совместимое устройство. Элементы доступны в списке ниже.',
    error: 'Не удалось запустить 3D или AR. Используйте текстовый вид или повторите загрузку.',
    alt: 'Три условных блока: энергия, вода и материалы',
    libraries: 'Каталог библиотек интеграции', ui: 'Интерактивный интерфейс', xr: 'AR и 3D',
    installed: 'Подключено', option: 'Вариант', language: 'Язык' },
  kk: { title: 'Интерактивті 3D және AR', demo: 'Эксперименттік көрсетілім',
    note: 'Көрнекі геометрия. Нақты нысанның өлшемдері мен расталған қорытындылар жоқ.',
    select: 'Элементті таңдаңыз', empty: 'Өлшемдер мен растайтын дереккөздер әлі қосылмаған.',
    load: '3D моделін жүктеу', loading: '3D моделі жүктелуде…', ar: 'Өз кеңістігіңізде көру',
    fallback: 'AR үшін HTTPS және үйлесімді құрылғы қажет. Төмендегі тізімді пайдалануға болады.',
    error: '3D немесе AR іске қосылмады. Мәтіндік көріністі пайдаланыңыз немесе қайта жүктеңіз.',
    alt: 'Энергия, су және материалдарға арналған үш шартты блок',
    libraries: 'Интеграция кітапханалары', ui: 'Интерактивті интерфейс', xr: 'AR және 3D',
    installed: 'Қосылған', option: 'Нұсқа', language: 'Тіл' },
  ar: { title: 'عرض تفاعلي ثلاثي الأبعاد وواقع معزز', demo: 'عرض تجريبي',
    note: 'أشكال توضيحية فقط. لا توجد قياسات لأصول حقيقية أو نتائج موثقة.',
    select: 'اختر جزءًا', empty: 'لم تُسجل قياسات أو أدلة داعمة بعد.',
    load: 'تحميل النموذج ثلاثي الأبعاد', loading: 'جارٍ تحميل النموذج…', ar: 'عرض في مساحتك',
    fallback: 'يتطلب الواقع المعزز HTTPS وجهازًا متوافقًا. يمكنك استخدام القائمة أدناه.',
    error: 'تعذر بدء العرض. استخدم العرض النصي أو حاول التحميل مجددًا.',
    alt: 'ثلاث كتل توضيحية للطاقة والمياه والمواد',
    libraries: 'مكتبات التكامل', ui: 'واجهة تفاعلية', xr: 'الواقع المعزز وثلاثي الأبعاد',
    installed: 'مدمج', option: 'خيار', language: 'اللغة' },
} as const;

export default function InteractiveLab() {
  const [language, setLanguage] = useState<Language>('en');
  const [selected, setSelected] = useState('energy');
  const state = useApi((signal) => getScene(language, signal), [language]);
  const libraries = useApi(getLibraries, []);
  const copy = COPY[language];
  return (
    <div className="interactive-lab" lang={language} dir={language === 'ar' ? 'rtl' : 'ltr'}>
      <header className="prose">
        <p className="status-badge status-badge--experimental">{copy.demo}</p>
        <h1>{copy.title}</h1>
        <p>{copy.note}</p>
        <label>{copy.language}{' '}
          <select value={language} onChange={(e) => setLanguage(e.target.value as Language)}>
            <option value="en">English</option><option value="ru">Русский</option>
            <option value="kk">Қазақша</option><option value="ar">العربية</option>
          </select>
        </label>
      </header>
      {state.status === 'loading' && <Loading label={copy.loading} />}
      {state.status === 'error' && <ErrorState error={state.error} />}
      {state.status === 'ready' && <>
        <ModelScene scene={state.data} labels={copy} selected={selected} onSelect={setSelected} />
        <section aria-labelledby="parts-heading">
          <h2 id="parts-heading">{copy.select}</h2>
          <div className="interactive-parts">
            {state.data.hotspots.map((part) => <button key={part.id} type="button"
              aria-pressed={selected === part.id} onClick={() => setSelected(part.id)}>{part.label}</button>)}
          </div>
          <div className="card" aria-live="polite">
            <h3>{state.data.hotspots.find((part) => part.id === selected)?.label}</h3>
            <p>{copy.empty}</p>
          </div>
        </section>
      </>}
      <details className="interactive-catalog">
        <summary>{copy.libraries}</summary>
        {libraries.status === 'loading' && <Loading />}
        {libraries.status === 'error' && <ErrorState error={libraries.error} />}
        {libraries.status === 'ready' && (['ui', 'ar'] as const).map((category) => (
          <section key={category}>
            <h2>{category === 'ui' ? copy.ui : copy.xr}</h2>
            <ul className="grid">
              {libraries.data.results.filter((item) => item.category === category).map((item) => (
                <li className="card" key={item.id}>
                  <a href={item.documentation_url}>{item.name}</a>
                  <p lang="en" dir="ltr">{item.purpose}</p>
                  <span>{item.status === 'INTEGRATED' ? copy.installed : copy.option}</span>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </details>
    </div>
  );
}
