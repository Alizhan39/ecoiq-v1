"""Twenty draft ecological stewardship lenses for EcoIQ.

These are EcoIQ-authored questions inspired by distinct religious source
traditions. They are NOT 20 Quran verses, fatwas, scholarly approvals or
mathematical definitions. All sources are locator hints only. No sacred
passages, translations, review receipts or credentials are fabricated.

Reuse the existing principle definitions for concepts already present in
islamic_knowledge.principles; this is not a second decision engine.
"""
from __future__ import annotations

from dataclasses import dataclass

from islamic_knowledge.catalog import QuranReference
from islamic_knowledge.contracts import PrincipleDefinition
from islamic_knowledge.principles import DRAFT_PRINCIPLES


SOURCE_FAMILIES = frozenset({'quran_concept', 'hadith_practice', 'fiqh_principle',
                             'ecoiq_application'})
HINT_TYPES = frozenset({'hadith', 'fiqh', 'historical'})


@dataclass(frozen=True)
class SourceHint:
    source_type: str
    locator: str
    url: str
    caution: str = 'Locator only; attribution, scope and interpretation need scholarly review.'

    def __post_init__(self):
        if self.source_type not in HINT_TYPES or not self.locator.strip():
            raise ValueError('Source hint must identify a supported tradition and locator.')
        if self.url and not self.url.startswith(('https://sunnah.com/', 'https://quran.com/')):
            raise ValueError('Source hints may link only to approved reference sites.')


@dataclass(frozen=True)
class StewardshipLens:
    concept: str
    arabic: str
    transliteration: str
    name_ru: str
    question_ru: str
    source_family: str
    context_note: str
    quran_locators: tuple[tuple[int, ...], ...] = ()
    other_sources: tuple[SourceHint, ...] = ()

    def __post_init__(self):
        if self.source_family not in SOURCE_FAMILIES:
            raise ValueError('Unknown source family.')
        if not all((self.concept, self.arabic, self.transliteration,
                    self.name_ru, self.question_ru, self.context_note)):
            raise ValueError('All lens identifiers and operational context are required.')
        for locator in self.quran_locators:
            QuranReference(*locator)  # validates the known Hafs ayah boundary

    @property
    def draft(self) -> PrincipleDefinition:
        canonical = {item.concept: item for item in DRAFT_PRINCIPLES}
        if self.concept in canonical:
            original = canonical[self.concept]
            if tuple(ref.locator for ref in original.quran_references) != tuple(
                QuranReference(*v).locator for v in self.quran_locators
            ):
                raise ValueError(f'Duplicate draft for {self.concept} has inconsistent Quran locators.')
            return original
        return PrincipleDefinition(
            id=f'ecoiq.{self.concept}.v1',
            concept=self.concept,
            version='1',
            statement=self.question_ru,
            scope=('Ecological stewardship and mining: EcoIQ draft application, '
                   'not a religious ruling, engineering threshold or permission.'),
            source_ids=(),
            quran_references=tuple(QuranReference(*ref) for ref in self.quran_locators),
        )


def _s(concept, arabic, transliteration, ru, question, family, note, refs=(), extra=()):
    return StewardshipLens(concept, arabic, transliteration, ru, question,
                           family, note, refs, extra)


STEWARDSHIP_LENSES = (
    _s('mizan', 'ميزان', 'Mizan', 'Равновесие',
       'Учитываются ли ресурсы, безопасность, люди и долгосрочный экологический баланс?',
       'quran_concept', 'Коран 55:7–9; инженерные пороги выводятся из измерений и норм, не из аята.',
       ((55, 7, 9),)),
    _s('khalifah', 'خليفة', 'Khalifah', 'Ответственное наместничество',
       'Кто несёт ответственность за землю, воду и будущие поколения?',
       'quran_concept', 'Коран 2:30 и 6:165; современное применение к недропользованию требует толкования.',
       ((2, 30), (6, 165))),
    _s('imarat_al_ard', 'عمارة الأرض', 'Imarat al-Ard', 'Обустройство Земли',
       'Оставляет ли проект устойчивую инфраструктуру и реальную пользу?',
       'quran_concept', '11:61 связано с заселением/освоением Земли; экологическое развитие — прикладное толкование.',
       ((11, 61),)),
    _s('islah', 'إصلاح', 'Islah', 'Исправление и восстановление',
       'Проверен ли план устранения ущерба и восстановления?',
       'quran_concept', '11:88 и 7:56; проект Islah проходит причинную и инженерную проверку.',
       ((11, 88), (7, 56))),
    _s('amanah', 'أمانة', 'Amanah', 'Доверенная ответственность',
       'Можно ли проследить обязательства, ответственных и доказательства исполнения?',
       'quran_concept', '4:58 относится к доверенным обязанностям; экологический аудит — EcoIQ-применение.',
       ((4, 58),)),
    _s('fasad', 'فساد في الأرض', 'Fasad fil-Ard', 'Разрушение и порча',
       'Есть ли измеренный вред и подтверждённый причинный механизм?',
       'quran_concept', '30:41; загрязнение само по себе не является религиозным приговором.',
       ((30, 41),)),
    _s('israf', 'إسراف', 'Israf', 'Чрезмерность и расточительство',
       'Сколько воды, энергии и материалов теряется без полезного результата?',
       'quran_concept', '7:31 — избегание чрезмерности; инженерный порог должен иметь источник.',
       ((7, 31),)),
    _s('tabdhir', 'تبذير', 'Tabdhir', 'Бессмысленная трата',
       'Какие материальные и финансовые потери можно предотвратить?',
       'quran_concept', '17:26–27: расточительство; не приравнивать любой CAPEX к растрате.',
       ((17, 26, 27),)),
    _s('iqtisad', 'اقتصاد', 'Iqtisad', 'Умеренность и соразмерность',
       'Соразмерны ли затраты, извлечённая польза и долгосрочный ущерб?',
       'quran_concept', '25:67 о соразмерности расходов; не прямая формула экономической эффективности.',
       ((25, 67),)),
    _s('tayyib', 'طيب', 'Tayyib', 'Доброкачественное и полезное',
       'Подтверждены ли качество, отсутствие опасных загрязнений и безопасность?',
       'quran_concept', '2:168 и 5:88 относятся в первую очередь к дозволенной доброй пище; перенос на добычу требует рассмотрения.',
       ((2, 168), (5, 88))),
    _s('hima', 'حمى', 'Hima', 'Охраняемая территория',
       'Проверены ли охраняемые участки и связанные права доступа?',
       'hadith_practice', 'Исторический режим пастбищ не эквивалентен современной лицензии на ООПТ.',
       extra=(SourceHint('hadith', 'Sahih al-Bukhari 2370', 'https://sunnah.com/bukhari:2370'),)),
    _s('harim', 'حريم', 'Harim', 'Защитная зона',
       'Проверены ли законные буферные зоны у водоисточников и иных объектов?',
       'fiqh_principle', 'Определение ширины буферов требует казахстанского права, гидрологии и анализа фикха.',
       extra=(SourceHint('fiqh', 'Classical fiqh: protective rights around wells and water sources', ''),)),
    _s('ihya_al_mawat', 'إحياء الموات', 'Ihya al-Mawat', 'Оживление неиспользуемой земли',
       'Есть ли законные права на использование земель и реальный план их восстановления?',
       'hadith_practice', 'Исторические нормы освоения земель не заменяют законные права землепользования.',
       extra=(SourceHint('historical', 'Muwatta Malik, Book 36: report of Umar on reviving land',
                         'https://sunnah.com/malik/36'),)),
    _s('ghars_al_ashjar', 'غرس الأشجار', 'Ghars al-Ashjar', 'Посадка деревьев',
       'Проводится ли восстановление растительности и подтверждена ли её приживаемость?',
       'hadith_practice', 'Количество посаженных деревьев не доказывает восстановление экосистемы.',
       extra=(SourceHint('hadith', 'Sahih al-Bukhari 2320', 'https://sunnah.com/bukhari:2320'),)),
    _s('rifq_bil_hayawan', 'الرفق بالحيوان', 'Rifq bil-Hayawan', 'Милосердие к животным',
       'Как проект измеряет риск вреда животным, местам обитания и путям миграции?',
       'hadith_practice', '6:38 описывает живые сообщества; животные и биоразнообразие требуют полевых данных.',
       ((6, 38),),
       (SourceHint('hadith', 'Sahih al-Bukhari 2363', 'https://sunnah.com/bukhari:2363'),)),
    _s('hifz_al_maa', 'حفظ الماء', 'Hifz al-Ma', 'Бережное отношение к воде',
       'Сколько пресной воды забирают, возвращают и загрязняют, включая бассейн реки?',
       'ecoiq_application', '21:30 указывает на жизненную важность воды, но не устанавливает норму м³/т.',
       ((21, 30),)),
    _s('la_darar_wa_la_dirar', 'لا ضرر ولا ضرار', 'La Darar wa La Dirar', 'Не причинять вред',
       'Выявлены ли неприемлемые угрозы людям, воде и экосистемам?',
       'hadith_practice', 'Фикх-принцип, основанный на хадисной традиции; проверять разночтения иснадов.',
       extra=(SourceHint('hadith', 'Forty Hadith an-Nawawi 32',
                         'https://sunnah.com/nawawi40:32',
                         'В сборнике Навави оценён как hasan; отдельные цепочки Ibn Majah 2340/2341 оценены как daif.'),)),
    _s('maslaha', 'مصلحة', 'Maslahah', 'Общественная польза',
       'Кто получает долгосрочную пользу и кто несёт расходы или риски?',
       'fiqh_principle', 'Методология усуль аль-фикх; не отдельная кораническая количественная формула.',
       extra=(SourceHint('fiqh', 'Usul al-fiqh: maslahah / public interest, school-dependent', ''),)),
    _s('dar_al_mafasid', 'درء المفاسد', 'Dar al-Mafasid', 'Предотвращение разрушительных последствий',
       'Проверены ли существенные риски до начала работ и применены меры предотвращения?',
       'fiqh_principle', 'Юридическая максима; оценивать виды вреда, доказательства и правовой контекст.',
       extra=(SourceHint('fiqh', 'Fiqh maxim: preventing harms, school/context dependent', ''),)),
    _s('sadaqa_jariya', 'صدقة جارية', 'Sadaqah Jariyah', 'Непрерывная благотворительность',
       'Существует ли отдельно проверяемый долговременный общественный результат?',
       'hadith_practice', 'Польза от благотворительности не равна финансовому ROI и не выводится из наличия рудника.',
       extra=(SourceHint('hadith', 'Sahih Muslim 1631', 'https://sunnah.com/muslim:1631'),)),
)

BY_CONCEPT = {lens.concept: lens for lens in STEWARDSHIP_LENSES}
if len(STEWARDSHIP_LENSES) != 20 or len(BY_CONCEPT) != 20:
    raise RuntimeError('The EcoIQ environmental stewardship registry must have 20 unique lenses.')


def stewardship_drafts() -> tuple[PrincipleDefinition, ...]:
    """Twenty versioned draft knowledge definitions, all requiring scholarly review."""
    return tuple(lens.draft for lens in STEWARDSHIP_LENSES)
