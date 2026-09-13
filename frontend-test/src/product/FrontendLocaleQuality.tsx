import { useEffect } from "react";

type Lang = "en" | "hy" | "ru";
type Dict = Record<string, string>;

const PROTECTED_PUBLIC = ".product-home-hero, .t2-navbar, .t2-footer";

const HY: Dict = {
  /* Dashboard / clinical shell */
  "Dashboard": "Գլխավոր վահանակ",
  "Patients & records": "Պացիենտներ և քարտեր",
  "OPG + AI": "OPG + AI",
  "Follow-up plans": "Հետագա վերահսկման պլաններ",
  "AI conversations": "Պացիենտների հետ զրույցներ",
  "Appointments": "Այցեր",
  "Working hours": "Աշխատանքային ժամեր",
  "Settings": "Կարգավորումներ",
  "Subscription": "Բաժանորդագրություն",
  "days left": "օր մնացել է",
  "Clinical action dashboard": "Կլինիկական գործողությունների վահանակ",
  "The OPG-to-follow-up loop, using live clinic data.": "OPG-ից մինչև հետագա վերահսկում՝ կլինիկայի իրական տվյալներով։",
  "Patients": "Պացիենտներ",
  "AI analyses": "AI վերլուծություններ",
  "Follow-ups due": "Ժամկետը հասած հետագա վերահսկումներ",
  "Active follow-up": "Ակտիվ հետագա վերահսկում",
  "Recent patients": "Վերջին պացիենտներ",
  "Follow-up actions": "Հետագա գործողություններ",
  "Search patients": "Փնտրել պացիենտ",
  "New patient": "Նոր պացիենտ",
  "Select a patient": "Ընտրել պացիենտ",
  "Smart Patient File": "Պացիենտի խելացի քարտ",
  "Overview": "Ընդհանուր տվյալներ",
  "OPG History": "OPG պատմություն",
  "Possible Findings": "Հնարավոր փոփոխություններ",
  "Follow-up": "Հետագա վերահսկում",
  "Messages": "Հաղորդագրություններ",
  "Phone": "Հեռախոս",
  "Email": "Էլ․ փոստ",
  "OPGs": "OPG-ներ",
  "Follow-ups": "Հետագա վերահսկումներ",
  "Latest AI-assisted analysis": "Վերջին AI-աջակցվող վերլուծություն",
  "Not analyzed": "Չվերլուծված",
  "No OPG history yet.": "OPG պատմություն դեռ չկա։",
  "No possible findings available.": "Հնարավոր փոփոխություններ չկան։",
  "Requires dentist examination": "Պահանջում է ատամնաբույժի գնահատում",
  "Sign out": "Դուրս գալ",
  "Notifications": "Ծանուցումներ",
  "Loading clinical workspace…": "Բեռնվում է կլինիկական աշխատանքային միջավայրը…",

  /* Analysis viewer */
  "No analysis selected": "Վերլուծություն ընտրված չէ",
  "Select an X-ray and run DENTAI V5.": "Ընտրեք ռենտգեն պատկերը և գործարկեք DENTAI V5-ը։",
  "Review saved.": "Վերանայումը պահպանվել է։",
  "Analysis failed": "Վերլուծությունը ձախողվել է",
  "Interactive OPG": "Ինտերակտիվ OPG",
  "DENTAI clinical findings on the radiograph": "DENTAI-ի կլինիկական արդյունքները ռենտգեն պատկերի վրա",
  "Green = treated or restored teeth · red = pathological findings · red intensity reflects model confidence.": "Կանաչ՝ բուժված կամ վերականգնված ատամներ · կարմիր՝ հնարավոր պաթոլոգիական փոփոխություններ · կարմիրի ուժգնությունը ցույց է տալիս մոդելի վստահության միավորը։",
  "AI report": "AI զեկույց",
  "AI overlay": "AI շերտ",
  "All": "Բոլորը",
  "Pending": "Սպասում է վերանայման",
  "Confirmed": "Հաստատված",
  "Rejected": "Մերժված",
  "The X-ray for this analysis is not available.": "Այս վերլուծության ռենտգեն պատկերը հասանելի չէ։",
  "Loading radiograph…": "Բեռնվում է ռենտգեն պատկերը…",
  "The radiograph could not be loaded.": "Չհաջողվեց բեռնել ռենտգեն պատկերը։",
  "AI clinical report": "AI կլինիկական զեկույց",
  "Key observation": "Հիմնական դիտարկում",
  "Monitoring": "Հետագա վերահսկում",
  "For the clinician": "Բժշկի ուշադրությանը",
  "AI summary does not replace clinician assessment.": "AI ամփոփումը չի փոխարինում բժշկի կլինիկական գնահատմանը։",
  "Finding review filters": "Արդյունքների վերանայման զտիչներ",
  "DENTAI clinical finding overlay": "DENTAI-ի կլինիկական արդյունքների շերտ",

  /* AI follow-up generation */
  "AI FOLLOW-UP ORCHESTRATION": "AI ՀԵՏԱԳԱ ՎԵՐԱՀՍԿՄԱՆ ԿԱՌԱՎԱՐՈՒՄ",
  "Waiting for analysis to complete": "Սպասում ենք վերլուծության ավարտին",
  "The Generate button will unlock automatically as soon as the current OPG analysis finishes. No page refresh is required.": "«Ստեղծել AI-ով» կոճակը կակտիվանա ավտոմատ, երբ ընթացիկ OPG վերլուծությունն ավարտվի։ Էջը թարմացնելու կարիք չկա։",
  "Generate with AI": "Ստեղծել AI-ով",
  "Follow-up plan ready": "Հետագա վերահսկման պլանը պատրաստ է",
  "Generate follow-up plan": "Ստեղծել հետագա վերահսկման պլան",
  "No pathological tooth findings with a resolved FDI are available in this completed OPG analysis.": "Այս ավարտված OPG վերլուծության մեջ FDI համարով նույնականացված և պլանում ընդգրկելու ենթակա պաթոլոգիական փոփոխություն չկա։",
  "Checking pathological tooth eligibility with the care backend…": "Ստուգվում է՝ որ ատամները կարող են ընդգրկվել հետագա վերահսկման պլանում…",
  "Open follow-up plans": "Բացել հետագա վերահսկման պլանները",
  "Generating…": "Ստեղծվում է…",
  "Clinician review is recommended; doctor remains in control.": "Խորհուրդ է տրվում բժշկի վերանայում․ վերջնական վերահսկողությունը մնում է բժշկին։",
  "Doctor remains in control": "Վերջնական վերահսկողությունը մնում է բժշկին",
  "Recommended: review AI findings before approving outreach, but generation is available now.": "Խորհուրդ է տրվում AI արդյունքները վերանայել նախքան պացիենտի հետ կապը հաստատելը, սակայն պլանը կարելի է ստեղծել արդեն հիմա։",

  /* Follow-up / WhatsApp */
  "CLINIC FOLLOW-UP QUEUE": "ԿԼԻՆԻԿԱՅԻ ՀԵՏԱԳԱ ՎԵՐԱՀՍԿՄԱՆ ՀԵՐԹ",
  "Patient follow-up plans": "Պացիենտների հետագա վերահսկման պլաններ",
  "One clinic WhatsApp connection serves all patients. Each patient keeps their own stored WhatsApp number and sequential tooth plan.": "Կլինիկայի մեկ WhatsApp կապն օգտագործվում է բոլոր պացիենտների համար։ Յուրաքանչյուր պացիենտի WhatsApp համարը և ատամների հերթական պլանը պահվում են առանձին։",
  "patient plans": "պացիենտի պլան",
  "Search patient, ID or WhatsApp": "Փնտրել պացիենտ, համար կամ WhatsApp",
  "Showing up to 200 recent plans": "Ցուցադրվում են մինչև 200 վերջին պլանները",
  "No matching follow-up plans.": "Համապատասխան հետագա վերահսկման պլան չի գտնվել։",
  "Patient": "Պացիենտ",
  "Not registered": "Գրանցված չէ",
  "Approve sequential outreach": "Հաստատել հերթական կապը պացիենտի հետ",
  "Activating…": "Ակտիվացվում է…",
  "Priority": "Առաջնահերթություն",
  "AI finding": "AI արդյունք",
  "Conversation start:": "Զրույցի մեկնարկ՝",
  "After previous tooth outcome": "Նախորդ ատամի վերջնական արդյունքից հետո",
  "Outcome:": "Արդյունք՝",
  "Clinical follow-up target": "Կլինիկական վերահսկման նպատակային ժամկետ",
  "Recommended window": "Առաջարկվող ժամանակահատված",
  "Rationale": "Հիմնավորում",
  "WhatsApp opening message": "WhatsApp-ի առաջին հաղորդագրություն",
  "Saving…": "Պահպանվում է…",
  "Save tooth plan": "Պահպանել ատամի պլանը",
  "CLINIC WHATSAPP": "ԿԼԻՆԻԿԱՅԻ WHATSAPP",
  "Clinic WhatsApp connected": "Կլինիկայի WhatsApp-ը միացված է",
  "Connect clinic WhatsApp": "Միացնել կլինիկայի WhatsApp-ը",
  "Connected": "Միացված է",
  "Disconnected": "Անջատված է",
  "Disconnect": "Անջատել",
  "Connect with QR": "Միացնել QR կոդով",
  "QR connect": "Միացնել QR-ով",
  "Scan QR to connect": "Սկանավորեք QR կոդը՝ միացնելու համար",
  "Generating QR…": "Ստեղծվում է QR կոդ…",
  "LIVE AI CONVERSATION": "AI-ԱՋԱԿՑՎՈՂ ԱԿՏԻՎ ԶՐՈՒՅՑ",
  "Patient conversation": "Զրույց պացիենտի հետ",
  "Every WhatsApp message is mirrored here.": "WhatsApp-ի յուրաքանչյուր հաղորդագրություն արտացոլվում է այստեղ։",
  "Live sync · 5s": "Ուղիղ համաժամացում · 5 վրկ",
  "APPOINTMENT AWAITING DOCTOR APPROVAL": "ԱՅՑԸ ՍՊԱՍՈՒՄ Է ԲԺՇԿԻ ՀԱՍՏԱՏՄԱՆԸ",
  "CONVERSATION APPOINTMENT": "ԶՐՈՒՅՑԻՆ ԿԱՊՎԱԾ ԱՅՑ",
  "No messages for this patient yet.": "Այս պացիենտի համար դեռ հաղորդագրություն չկա։",
  "VISIT OUTCOME → AI FOLLOW-UP": "ԱՅՑԻ ԱՐԴՅՈՒՆՔ → AI ՀԵՏԱԳԱ ՎԵՐԱՀՍԿՈՒՄ",
  "Appointment outcomes": "Այցերի վերջնական արդյունքներ",
  "Record what actually happened. Teta2 uses the outcome to continue the current tooth or unlock the next priority tooth.": "Գրանցեք այցի իրական արդյունքը։ Teta2-ն այն օգտագործում է ընթացիկ ատամի փուլը շարունակելու կամ հաջորդ առաջնահերթ ատամն ակտիվացնելու համար։",
  "Optional clinical note": "Կլինիկական նշում (ըստ ցանկության)",
  "Came · treated": "Այցելել է · բուժվել է",
  "Came · not treated": "Այցելել է · բուժում չի կատարվել",
  "No-show": "Չի ներկայացել",

  /* Case workspace */
  "Not scheduled": "Պլանավորված չէ",
  "FOLLOW-UP CASES": "ՀԵՏԱԳԱ ՎԵՐԱՀՍԿՄԱՆ ԳՈՐԾԵՐ",
  "Patient follow-up workspace": "Պացիենտների հետագա վերահսկման միջավայր",
  "One patient = one organized case file. All dates are shown in the clinic timezone.": "Յուրաքանչյուր պացիենտ ունի առանձին կազմակերպված գործ։ Բոլոր ամսաթվերը ցուցադրվում են կլինիկայի ժամային գոտով։",
  "Clinic timezone": "Կլինիկայի ժամային գոտի",
  "No matching patient cases.": "Համապատասխան պացիենտի գործ չի գտնվել։",
  "No follow-up case selected.": "Հետագա վերահսկման գործ ընտրված չէ։",
  "Clinic WhatsApp": "Կլինիկայի WhatsApp",
  "PATIENT FOLLOW-UP FILE": "ՊԱՑԻԵՆՏԻ ՀԵՏԱԳԱ ՎԵՐԱՀՍԿՄԱՆ ԳՈՐԾ",
  "WhatsApp not registered": "WhatsApp համարը գրանցված չէ",
  "Approve outreach": "Հաստատել կապը պացիենտի հետ",
  "Teeth in plan": "Պլանում ընդգրկված ատամներ",
  "Current tooth": "Ընթացիկ ատամ",
  "First outreach": "Առաջին կապ",
  "Timezone": "Ժամային գոտի",
  "FIRST WHATSAPP OUTREACH": "WHATSAPP-Ի ԱՌԱՋԻՆ ՀԱՂՈՐԴԱԳՐՈՒԹՅՈՒՆ",
  "Doctor can change this before the first message is sent": "Բժիշկը կարող է փոխել ժամը մինչև առաջին հաղորդագրության ուղարկումը",
  "Scheduled outreach": "Պլանավորված կապ",
  "This controls when the AI sends the opening WhatsApp message for the first priority tooth.": "Այստեղ սահմանվում է, թե երբ AI-ը կուղարկի WhatsApp-ի առաջին հաղորդագրությունը առաջին առաջնահերթ ատամի համար։",
  "Save send time": "Պահպանել ուղարկման ժամը",
  "TREATMENT FOLLOW-UP SEQUENCE": "ԲՈՒԺՄԱՆ ՀԵՏԱԳԱ ՎԵՐԱՀՍԿՄԱՆ ՀԵՐԹԱԿԱՆՈՒԹՅՈՒՆ",
  "Tooth-by-tooth plan": "Պլան՝ ատամ առ ատամ",
  "Later teeth unlock only after the previous outcome.": "Հաջորդ ատամներն ակտիվանում են միայն նախորդ փուլի վերջնական արդյունքից հետո։",
  "Clinical follow-up": "Կլինիկական հետագա վերահսկում",
  "Opening message will be prepared before outreach.": "Առաջին հաղորդագրությունը կպատրաստվի կապը սկսելուց առաջ։",

  /* Login / access */
  "Use the clinic slug and account provisioned for your clinic.": "Օգտագործեք կլինիկայի ակտիվացման ժամանակ տրամադրված նույնականացուցիչն ու հաշիվը։",
  "Clinic slug": "Կլինիկայի նույնականացուցիչ",
  "SECURE CLINIC ACCESS": "ԱՆՎՏԱՆԳ ՄՈՒՏՔ ԿԼԻՆԻԿԱՅԻ ՀԱՄԱՐ",
  "Clinician-controlled · Patient-specific · Follow-up visible": "Բժիշկը վերահսկում է · Անհատական պացիենտի համար · Հետագա վերահսկումը տեսանելի է",
  "Request submitted": "Հայտն ուղարկված է",
  "Back to Teta2": "Վերադառնալ Teta2",
  "Clinic name *": "Կլինիկայի անվանում *",
  "Country *": "Երկիր *",
  "Select market": "Ընտրեք շուկան",
  "Armenia": "Հայաստան",
  "Russia": "Ռուսաստան",
  "City *": "Քաղաք *",
  "Clinic address": "Կլինիկայի հասցե",
  "Website": "Կայք",
  "Contact person *": "Կոնտակտային անձ *",
  "Role / title *": "Պաշտոն / դեր *",
  "Director, owner, dentist…": "Տնօրեն, սեփականատեր, ատամնաբույժ…",
  "Email *": "Էլ․ փոստ *",
  "Phone *": "Հեռախոս *",
  "Number of dentists *": "Ատամնաբույժների քանակ *",
  "Number of branches *": "Մասնաճյուղերի քանակ *",
  "Anything we should know?": "Կա՞ որևէ լրացուցիչ տեղեկություն, որ պետք է իմանանք։",

  /* Legal shell */
  "Trust center": "Իրավական և վստահության կենտրոն",
  "LEGAL & TRUST": "ԻՐԱՎԱԿԱՆ ԵՎ ՎՍՏԱՀՈՒԹՅՈՒՆ",
  "TRANSPARENCY": "ԹԱՓԱՆՑԻԿՈՒԹՅՈՒՆ",
  "COMMERCIAL TERMS": "ԱՌԵՎՏՐԱՅԻՆ ՊԱՅՄԱՆՆԵՐ",
  "CLINICAL SAFETY": "ԿԼԻՆԻԿԱԿԱՆ ԱՆՎՏԱՆԳՈՒԹՅՈՒՆ",

  /* Finding labels */
  "Apical change": "Ապիկալ փոփոխություն",
  "Apical periodontitis": "Ապիկալ պերիօդոնտիտ",
  "Bone loss": "Ոսկրային կորստի նշան",
  "Bone resorption": "Ոսկրային ռեզորբցիա",
  "Bridge": "Կամուրջ",
  "Caries": "Կարիես",
  "Crown": "Պսակ",
  "Deep caries": "Խորը կարիես",
  "Filling": "Լցոնում",
  "Furcation change": "Ֆուրկացիոն փոփոխություն",
  "Furcation lesion": "Ֆուրկացիոն ախտահարում",
  "Impacted tooth": "Չծկթած ատամ",
  "Implant": "Իմպլանտ",
  "Residual root": "Մնացորդային արմատ",
  "Restoration": "Վերականգնում",
  "Root canal treatment": "Արմատախողովակային բուժում",
  "Root canal filling": "Արմատախողովակային լցոնում",
  "Root fragment": "Արմատի հատված",
};

const RU: Dict = {
  "Dashboard": "Главная",
  "Patients & records": "Пациенты и карты",
  "OPG + AI": "OPG + ИИ",
  "Follow-up plans": "Планы наблюдения",
  "AI conversations": "Диалоги с пациентами",
  "Appointments": "Приемы",
  "Working hours": "Рабочие часы",
  "Settings": "Настройки",
  "Subscription": "Подписка",
  "days left": "дней осталось",
  "Clinical action dashboard": "Панель клинических действий",
  "The OPG-to-follow-up loop, using live clinic data.": "От OPG до последующего наблюдения — на реальных данных клиники.",
  "Patients": "Пациенты",
  "AI analyses": "Анализы ИИ",
  "Follow-ups due": "Наблюдения к выполнению",
  "Active follow-up": "Активное наблюдение",
  "Recent patients": "Недавние пациенты",
  "Follow-up actions": "Действия по наблюдению",
  "Search patients": "Поиск пациентов",
  "New patient": "Новый пациент",
  "Select a patient": "Выберите пациента",
  "Smart Patient File": "Умная карта пациента",
  "Overview": "Обзор",
  "OPG History": "История OPG",
  "Possible Findings": "Возможные изменения",
  "Follow-up": "Наблюдение",
  "Messages": "Сообщения",
  "Phone": "Телефон",
  "Email": "Email",
  "OPGs": "OPG",
  "Follow-ups": "Наблюдения",
  "Latest AI-assisted analysis": "Последний анализ с поддержкой ИИ",
  "Not analyzed": "Не проанализировано",
  "No OPG history yet.": "Истории OPG пока нет.",
  "No possible findings available.": "Возможных изменений нет.",
  "Requires dentist examination": "Требуется оценка стоматолога",
  "Sign out": "Выйти",
  "Notifications": "Уведомления",
  "Loading clinical workspace…": "Загрузка клинического рабочего пространства…",

  "No analysis selected": "Анализ не выбран",
  "Select an X-ray and run DENTAI V5.": "Выберите рентгеновский снимок и запустите DENTAI V5.",
  "Review saved.": "Результаты проверки сохранены.",
  "Analysis failed": "Не удалось выполнить анализ",
  "Interactive OPG": "Интерактивный OPG",
  "DENTAI clinical findings on the radiograph": "Клинические результаты DENTAI на рентгеновском снимке",
  "Green = treated or restored teeth · red = pathological findings · red intensity reflects model confidence.": "Зеленым отмечены пролеченные или восстановленные зубы · красным — возможные патологические изменения · интенсивность красного отражает уверенность модели.",
  "AI report": "Отчет ИИ",
  "AI overlay": "Слой ИИ",
  "All": "Все",
  "Pending": "Ожидает проверки",
  "Confirmed": "Подтверждено",
  "Rejected": "Отклонено",
  "The X-ray for this analysis is not available.": "Рентгеновский снимок для этого анализа недоступен.",
  "Loading radiograph…": "Загрузка рентгеновского снимка…",
  "The radiograph could not be loaded.": "Не удалось загрузить рентгеновский снимок.",
  "AI clinical report": "Клинический отчет ИИ",
  "Key observation": "Ключевое наблюдение",
  "Monitoring": "Наблюдение",
  "For the clinician": "Для врача",
  "AI summary does not replace clinician assessment.": "Резюме ИИ не заменяет оценку врача.",
  "Finding review filters": "Фильтры проверки результатов",
  "DENTAI clinical finding overlay": "Слой клинических результатов DENTAI",

  "AI FOLLOW-UP ORCHESTRATION": "УПРАВЛЕНИЕ ПОСЛЕДУЮЩИМ НАБЛЮДЕНИЕМ С ИИ",
  "Waiting for analysis to complete": "Ожидание завершения анализа",
  "The Generate button will unlock automatically as soon as the current OPG analysis finishes. No page refresh is required.": "Кнопка «Создать с ИИ» активируется автоматически после завершения текущего анализа OPG. Обновлять страницу не нужно.",
  "Generate with AI": "Создать с ИИ",
  "Follow-up plan ready": "План наблюдения готов",
  "Generate follow-up plan": "Создать план наблюдения",
  "No pathological tooth findings with a resolved FDI are available in this completed OPG analysis.": "В завершенном анализе OPG нет патологических изменений с определенным номером FDI, которые можно включить в план наблюдения.",
  "Checking pathological tooth eligibility with the care backend…": "Проверяем, какие зубы можно включить в план наблюдения…",
  "Open follow-up plans": "Открыть планы наблюдения",
  "Generating…": "Создание…",
  "Clinician review is recommended; doctor remains in control.": "Рекомендуется проверка врачом; окончательное решение остается за врачом.",
  "Doctor remains in control": "Окончательное решение остается за врачом",
  "Recommended: review AI findings before approving outreach, but generation is available now.": "Рекомендуется проверить результаты ИИ до начала связи с пациентом, однако план можно создать уже сейчас.",

  "CLINIC FOLLOW-UP QUEUE": "ОЧЕРЕДЬ ПОСЛЕДУЮЩЕГО НАБЛЮДЕНИЯ",
  "Patient follow-up plans": "Планы наблюдения пациентов",
  "One clinic WhatsApp connection serves all patients. Each patient keeps their own stored WhatsApp number and sequential tooth plan.": "Одно подключение WhatsApp клиники используется для всех пациентов. Номер WhatsApp и последовательный план по зубам хранятся отдельно для каждого пациента.",
  "patient plans": "планов пациентов",
  "Search patient, ID or WhatsApp": "Поиск по пациенту, номеру или WhatsApp",
  "Showing up to 200 recent plans": "Показаны до 200 последних планов",
  "No matching follow-up plans.": "Подходящих планов наблюдения не найдено.",
  "Patient": "Пациент",
  "Not registered": "Не указан",
  "Approve sequential outreach": "Подтвердить последовательную связь с пациентом",
  "Activating…": "Активация…",
  "Priority": "Приоритет",
  "AI finding": "Результат ИИ",
  "Conversation start:": "Начало диалога:",
  "After previous tooth outcome": "После итогового результата по предыдущему зубу",
  "Outcome:": "Результат:",
  "Clinical follow-up target": "Целевая дата клинического наблюдения",
  "Recommended window": "Рекомендуемый период",
  "Rationale": "Обоснование",
  "WhatsApp opening message": "Первое сообщение WhatsApp",
  "Saving…": "Сохранение…",
  "Save tooth plan": "Сохранить план по зубу",
  "CLINIC WHATSAPP": "WHATSAPP КЛИНИКИ",
  "Clinic WhatsApp connected": "WhatsApp клиники подключен",
  "Connect clinic WhatsApp": "Подключить WhatsApp клиники",
  "Connected": "Подключен",
  "Disconnected": "Не подключен",
  "Disconnect": "Отключить",
  "Connect with QR": "Подключить по QR-коду",
  "QR connect": "Подключить по QR",
  "Scan QR to connect": "Отсканируйте QR-код для подключения",
  "Generating QR…": "Создание QR-кода…",
  "LIVE AI CONVERSATION": "АКТИВНЫЙ ДИАЛОГ С ПОДДЕРЖКОЙ ИИ",
  "Patient conversation": "Диалог с пациентом",
  "Every WhatsApp message is mirrored here.": "Здесь отображается каждое сообщение WhatsApp.",
  "Live sync · 5s": "Синхронизация · 5 с",
  "APPOINTMENT AWAITING DOCTOR APPROVAL": "ПРИЕМ ОЖИДАЕТ ПОДТВЕРЖДЕНИЯ ВРАЧА",
  "CONVERSATION APPOINTMENT": "ПРИЕМ, СВЯЗАННЫЙ С ДИАЛОГОМ",
  "No messages for this patient yet.": "Для этого пациента сообщений пока нет.",
  "VISIT OUTCOME → AI FOLLOW-UP": "РЕЗУЛЬТАТ ПРИЕМА → ПОСЛЕДУЮЩЕЕ НАБЛЮДЕНИЕ С ИИ",
  "Appointment outcomes": "Итоги приемов",
  "Record what actually happened. Teta2 uses the outcome to continue the current tooth or unlock the next priority tooth.": "Зафиксируйте фактический результат приема. Teta2 использует его, чтобы продолжить этап по текущему зубу или открыть следующий приоритетный зуб.",
  "Optional clinical note": "Клиническая заметка (необязательно)",
  "Came · treated": "Пришел · лечение проведено",
  "Came · not treated": "Пришел · без лечения",
  "No-show": "Не явился",

  "Not scheduled": "Не запланировано",
  "FOLLOW-UP CASES": "СЛУЧАИ ПОСЛЕДУЮЩЕГО НАБЛЮДЕНИЯ",
  "Patient follow-up workspace": "Рабочее пространство наблюдения пациентов",
  "One patient = one organized case file. All dates are shown in the clinic timezone.": "Для каждого пациента ведется отдельное организованное дело. Все даты показаны в часовом поясе клиники.",
  "Clinic timezone": "Часовой пояс клиники",
  "No matching patient cases.": "Подходящих случаев не найдено.",
  "No follow-up case selected.": "Случай наблюдения не выбран.",
  "Clinic WhatsApp": "WhatsApp клиники",
  "PATIENT FOLLOW-UP FILE": "КАРТА ПОСЛЕДУЮЩЕГО НАБЛЮДЕНИЯ",
  "WhatsApp not registered": "WhatsApp не указан",
  "Approve outreach": "Подтвердить связь с пациентом",
  "Teeth in plan": "Зубов в плане",
  "Current tooth": "Текущий зуб",
  "First outreach": "Первая связь",
  "Timezone": "Часовой пояс",
  "FIRST WHATSAPP OUTREACH": "ПЕРВОЕ СООБЩЕНИЕ WHATSAPP",
  "Doctor can change this before the first message is sent": "Врач может изменить время до отправки первого сообщения",
  "Scheduled outreach": "Запланированная связь",
  "This controls when the AI sends the opening WhatsApp message for the first priority tooth.": "Здесь задается время, когда ИИ отправит первое сообщение WhatsApp по первому приоритетному зубу.",
  "Save send time": "Сохранить время отправки",
  "TREATMENT FOLLOW-UP SEQUENCE": "ПОСЛЕДОВАТЕЛЬНОСТЬ ПОСЛЕДУЮЩЕГО НАБЛЮДЕНИЯ",
  "Tooth-by-tooth plan": "План по каждому зубу",
  "Later teeth unlock only after the previous outcome.": "Следующий зуб становится доступен только после фиксации результата предыдущего этапа.",
  "Clinical follow-up": "Клиническое наблюдение",
  "Opening message will be prepared before outreach.": "Первое сообщение будет подготовлено до начала связи с пациентом.",

  "Use the clinic slug and account provisioned for your clinic.": "Используйте идентификатор клиники и учетную запись, полученные при активации.",
  "Clinic slug": "Идентификатор клиники",
  "SECURE CLINIC ACCESS": "БЕЗОПАСНЫЙ ДОСТУП ДЛЯ КЛИНИКИ",
  "Clinician-controlled · Patient-specific · Follow-up visible": "Под контролем врача · Для конкретного пациента · Наблюдение остается видимым",
  "Request submitted": "Заявка отправлена",
  "Back to Teta2": "Вернуться в Teta2",
  "Clinic name *": "Название клиники *",
  "Country *": "Страна *",
  "Select market": "Выберите рынок",
  "Armenia": "Армения",
  "Russia": "Россия",
  "City *": "Город *",
  "Clinic address": "Адрес клиники",
  "Website": "Сайт",
  "Contact person *": "Контактное лицо *",
  "Role / title *": "Должность / роль *",
  "Director, owner, dentist…": "Директор, владелец, стоматолог…",
  "Email *": "Email *",
  "Phone *": "Телефон *",
  "Number of dentists *": "Количество стоматологов *",
  "Number of branches *": "Количество филиалов *",
  "Anything we should know?": "Что еще нам важно знать?",

  "Trust center": "Центр доверия и правовой информации",
  "LEGAL & TRUST": "ПРАВОВАЯ ИНФОРМАЦИЯ И ДОВЕРИЕ",
  "TRANSPARENCY": "ПРОЗРАЧНОСТЬ",
  "COMMERCIAL TERMS": "КОММЕРЧЕСКИЕ УСЛОВИЯ",
  "CLINICAL SAFETY": "КЛИНИЧЕСКАЯ БЕЗОПАСНОСТЬ",

  "Apical change": "Апикальное изменение",
  "Apical periodontitis": "Апикальный периодонтит",
  "Bone loss": "Признак потери костной ткани",
  "Bone resorption": "Резорбция костной ткани",
  "Bridge": "Мостовидный протез",
  "Caries": "Кариес",
  "Crown": "Коронка",
  "Deep caries": "Глубокий кариес",
  "Filling": "Пломба",
  "Furcation change": "Изменение в области фуркации",
  "Furcation lesion": "Поражение фуркации",
  "Impacted tooth": "Ретинированный зуб",
  "Implant": "Имплантат",
  "Residual root": "Остаточный корень",
  "Restoration": "Реставрация",
  "Root canal treatment": "Эндодонтическое лечение",
  "Root canal filling": "Пломбирование корневого канала",
  "Root fragment": "Фрагмент корня",
};

const STATUS_HY: Dict = {
  "Pending Approval": "Սպասում է հաստատման",
  "Active": "Ակտիվ",
  "Paused": "Դադարեցված",
  "Completed": "Ավարտված",
  "Followup Ready": "Պատրաստ է հետագա վերահսկման",
  "Waiting Previous Tooth": "Սպասում է նախորդ ատամի փուլին",
  "Contacted": "Կապ է հաստատվել",
  "Booked": "Ամրագրված",
  "Proposed": "Առաջարկված",
  "Approved": "Հաստատված",
  "Confirmed": "Հաստատված",
  "Rejected": "Մերժված",
  "Cancelled": "Չեղարկված",
  "Treated": "Բուժված",
  "Attended Not Treated": "Այցելել է՝ առանց բուժման",
  "No Show": "Չի ներկայացել",
  "Pending": "Սպասման մեջ",
  "Sending": "Ուղարկվում է",
  "Sent": "Ուղարկված",
  "Failed": "Չհաջողվեց",
  "Queued": "Հերթում",
  "Processing": "Մշակվում է",
  "Unreviewed": "Չվերանայված",
  "Reviewed": "Վերանայված",
};

const STATUS_RU: Dict = {
  "Pending Approval": "Ожидает подтверждения",
  "Active": "Активен",
  "Paused": "Приостановлен",
  "Completed": "Завершен",
  "Followup Ready": "Готов к наблюдению",
  "Waiting Previous Tooth": "Ожидает завершения предыдущего зуба",
  "Contacted": "Связь установлена",
  "Booked": "Записан",
  "Proposed": "Предложено",
  "Approved": "Подтверждено",
  "Confirmed": "Подтверждено",
  "Rejected": "Отклонено",
  "Cancelled": "Отменено",
  "Treated": "Лечение проведено",
  "Attended Not Treated": "Прием состоялся без лечения",
  "No Show": "Не явился",
  "Pending": "Ожидает",
  "Sending": "Отправляется",
  "Sent": "Отправлено",
  "Failed": "Ошибка",
  "Queued": "В очереди",
  "Processing": "Обрабатывается",
  "Unreviewed": "Не проверено",
  "Reviewed": "Проверено",
};

/* The five navbar content pages currently contain older hybrid Armenian/Russian copy.
   These replacements only run inside .deck2 and deliberately do not touch the protected
   homepage hero, public navbar or footer. */
const PAGE_HY: Dict = {
  "Մեկ clinical loop՝ կառուցված պացիենտի, ոչ թե առանձին AI արդյունքի շուրջ։": "Մեկ կլինիկական շղթա՝ կառուցված պացիենտի, ոչ թե առանձին AI արդյունքի շուրջ։",
  "Teta2-ը կապում է panoramic image-ը, AI-assisted possible findings-ը, clinician review-ը, patient record-ը և follow-up-ը մեկ տեսանելի workflow-ում։": "Teta2-ը միավորում է պանորամիկ պատկերը, AI-աջակցվող հնարավոր փոփոխությունները, բժշկի վերանայումը, պացիենտի քարտը և հետագա վերահսկումը մեկ տեսանելի գործընթացում։",
  "AI-assisted review": "AI-աջակցվող վերանայում",
  "Follow-up-ը մնում է տեսանելի": "Հետագա վերահսկումը մնում է տեսանելի",
  "PATIENT WORKSPACE": "ՊԱՑԻԵՆՏԻ ԱՇԽԱՏԱՆՔԱՅԻՆ ՄԻՋԱՎԱՅՐ",
  "Օգտակար միավորը մեկ նկար չէ։ Դա պացիենտի clinical continuity-ն է։": "Արժեքը միայն մեկ պատկերում չէ․ կարևոր է պացիենտի կլինիկական շարունակականությունը։",
  "Patient identity & contact": "Պացիենտի տվյալներ և կապ",
  "OPG history": "OPG պատմություն",
  "Possible findings": "Հնարավոր փոփոխություններ",
  "Review state": "Վերանայման կարգավիճակ",
  "Follow-up timing": "Հետագա վերահսկման ժամանակացույց",
  "Message state": "Հաղորդագրության կարգավիճակ",
  "Clinical": "Կլինիկական",
  "Patient": "Պացիենտ",
  "Follow-up": "Հետագա վերահսկում",
  "WORKFLOW, ՈՉ BLACK BOX": "ԳՈՐԾԸՆԹԱՑ, ՈՉ ԹԵ «ՍԵՎ ԱՐԿՂ»",
  "Create patient": "Ստեղծել պացիենտ",
  "Upload OPG": "Վերբեռնել OPG",
  "AI-assisted analysis": "AI-աջակցվող վերլուծություն",
  "Clinical review": "Կլինիկական վերանայում",
  "Keep the record": "Պահպանել քարտում",
  "Set follow-up": "Սահմանել հետագա վերահսկումը",
  "Send outreach": "Կապ հաստատել պացիենտի հետ",
  "Track return": "Հետևել վերադարձին",
  "STATE MACHINE": "ԿԱՐԳԱՎԻՃԱԿՆԵՐԻ ՇՂԹԱ",
  "AUTOMATION BOUNDARY": "ԱՎՏՈՄԱՏԱՑՄԱՆ ՍԱՀՄԱՆՆԵՐ",
  "CLINIC SUBSCRIPTION": "ԿԼԻՆԻԿԱՅԻ ԲԱԺԱՆՈՐԴԱԳՐՈՒԹՅՈՒՆ",
  "Երկու շուկա։ Մեկ պարզ monthly subscription model։": "Երկու շուկա։ Մեկ պարզ ամսական բաժանորդագրություն։",
  "Առաջին 50 clinics": "Առաջին 50 կլինիկաները",
  "ACCESS PROCESS": "ՄՈՒՏՔԻ ԳՈՐԾԸՆԹԱՑ",
  "CLINICAL SAFETY": "ԿԼԻՆԻԿԱԿԱՆ ԱՆՎՏԱՆԳՈՒԹՅՈՒՆ",
  "HUMAN IN THE LOOP": "ՄԱՍՆԱԳԵՏԸ ՄՆՈՒՄ Է ԳՈՐԾԸՆԹԱՑՈՒՄ",
  "IMAGING CONTEXT": "ՊԱՏԿԵՐԱՅԻՆ ՀԱՄԱՏԵՔՍՏ",
  "OPERATIONAL HONESTY": "ԳՈՐԾԱՌՆԱԿԱՆ ԹԱՓԱՆՑԻԿՈՒԹՅՈՒՆ",
  "Founder · Teta2": "Հիմնադիր · Teta2",
  "Co-founder · Technical / AI model fine-tuning": "Համահիմնադիր · տեխնիկական աշխատանք / AI մոդելի ճշգրտում",
  "Public profile": "Հանրային պրոֆիլ",
  "Public source": "Հանրային աղբյուր",
};

const PAGE_RU: Dict = {
  "Один clinical loop вокруг пациента, а не вокруг отдельного AI-результата.": "Один клинический цикл вокруг пациента, а не вокруг отдельного результата ИИ.",
  "Teta2 связывает панорамный снимок, AI-assisted possible findings, review врача, patient record и follow-up в один видимый workflow.": "Teta2 объединяет панорамный снимок, возможные изменения с поддержкой ИИ, проверку врачом, карту пациента и последующее наблюдение в один прозрачный рабочий процесс.",
  "AI-assisted review": "Проверка с поддержкой ИИ",
  "Follow-up остается видимым": "Последующее наблюдение остается видимым",
  "PATIENT WORKSPACE": "РАБОЧЕЕ ПРОСТРАНСТВО ПАЦИЕНТА",
  "Patient identity & contact": "Данные пациента и контакты",
  "OPG history": "История OPG",
  "Possible findings": "Возможные изменения",
  "Review state": "Статус проверки",
  "Follow-up timing": "Сроки наблюдения",
  "Message state": "Статус сообщений",
  "Clinical": "Клинический уровень",
  "Patient": "Пациент",
  "Follow-up": "Наблюдение",
  "WORKFLOW, А НЕ BLACK BOX": "РАБОЧИЙ ПРОЦЕСС, А НЕ «ЧЕРНЫЙ ЯЩИК»",
  "Create patient": "Создать пациента",
  "Upload OPG": "Загрузить OPG",
  "AI-assisted analysis": "Анализ с поддержкой ИИ",
  "Clinical review": "Клиническая проверка",
  "Keep the record": "Сохранить в карте",
  "Set follow-up": "Назначить наблюдение",
  "Send outreach": "Связаться с пациентом",
  "Track return": "Отслеживать возвращение",
  "STATE MACHINE": "ЦЕПОЧКА СТАТУСОВ",
  "AUTOMATION BOUNDARY": "ГРАНИЦЫ АВТОМАТИЗАЦИИ",
  "CLINIC SUBSCRIPTION": "ПОДПИСКА ДЛЯ КЛИНИКИ",
  "Два рынка. Одна понятная monthly subscription model.": "Два рынка. Одна понятная модель ежемесячной подписки.",
  "Первые 50 clinics": "Первые 50 клиник",
  "ACCESS PROCESS": "ПРОЦЕСС ДОСТУПА",
  "CLINICAL SAFETY": "КЛИНИЧЕСКАЯ БЕЗОПАСНОСТЬ",
  "HUMAN IN THE LOOP": "СПЕЦИАЛИСТ ОСТАЕТСЯ В ПРОЦЕССЕ",
  "IMAGING CONTEXT": "КОНТЕКСТ ВИЗУАЛИЗАЦИИ",
  "OPERATIONAL HONESTY": "ОПЕРАЦИОННАЯ ПРОЗРАЧНОСТЬ",
  "Founder · Teta2": "Основатель · Teta2",
  "Co-founder · Technical / AI model fine-tuning": "Сооснователь · техническая работа / донастройка модели ИИ",
  "Public profile": "Публичный профиль",
  "Public source": "Публичный источник",
};

const PAGE_RULES_HY: Array<[RegExp, string]> = [
  [/\bfollow-up\b/gi, "հետագա վերահսկում"],
  [/\bworkflow\b/gi, "գործընթաց"],
  [/\bworkspace\b/gi, "աշխատանքային միջավայր"],
  [/\bpatient record\b/gi, "պացիենտի քարտ"],
  [/\bpossible findings\b/gi, "հնարավոր փոփոխություններ"],
  [/\bpossible finding\b/gi, "հնարավոր փոփոխություն"],
  [/\bclinician\b/gi, "բժիշկ"],
  [/\bdentist\b/gi, "ատամնաբույժ"],
  [/\breview\b/gi, "վերանայում"],
  [/\boutreach\b/gi, "կապ պացիենտի հետ"],
  [/\bsubscription\b/gi, "բաժանորդագրություն"],
  [/\bsite\b/gi, "կայք"],
  [/\bproject\b/gi, "նախագիծ"],
];

const PAGE_RULES_RU: Array<[RegExp, string]> = [
  [/\bfollow-up\b/gi, "последующее наблюдение"],
  [/\bworkflow\b/gi, "рабочий процесс"],
  [/\bworkspace\b/gi, "рабочее пространство"],
  [/\bpatient record\b/gi, "карта пациента"],
  [/\bpossible findings\b/gi, "возможные изменения"],
  [/\bpossible finding\b/gi, "возможное изменение"],
  [/\bclinician\b/gi, "врач"],
  [/\bdentist\b/gi, "стоматолог"],
  [/\breview\b/gi, "проверка"],
  [/\boutreach\b/gi, "связь с пациентом"],
  [/\bsubscription\b/gi, "подписка"],
];

const LEGAL_HY: Dict = {
  "The rules governing access to and use of the Teta2 clinical software platform.": "Teta2 կլինիկական ծրագրային հարթակ մուտք գործելու և այն օգտագործելու կանոնները։",
  "How Teta2 handles clinic applications, account information, patient records, OPG images and clinical workflow data.": "Ինչպես է Teta2-ը մշակում կլինիկայի հայտերը, հաշվի տվյալները, պացիենտների քարտերը, OPG պատկերները և կլինիկական գործընթացի տվյալները։",
  "A precise list of what the current Teta2 frontend stores in your browser.": "Ճշգրիտ ցանկ այն տվյալների, որոնք Teta2-ի ներկայիս ֆրոնտենդը պահում է ձեր դիտարկչում։",
  "How the current clinic subscription payment process actually works.": "Ինչպես է իրականում աշխատում կլինիկայի ներկայիս բաժանորդագրության վճարման գործընթացը։",
  "The boundaries of Teta2's OPG analysis and follow-up assistance.": "Teta2-ի OPG վերլուծության և հետագա վերահսկման աջակցության սահմանները։",
  "1. Scope and roles": "1. Կիրառման շրջանակը և դերերը",
  "2. Information processed": "2. Մշակվող տեղեկությունները",
  "3. Purposes and legal grounds": "3. Նպատակները և իրավական հիմքերը",
  "4. Infrastructure and recipients": "4. Ենթակառուցվածքը և տվյալների ստացողները",
  "5. Retention": "5. Պահպանման ժամկետը",
  "6. Security": "6. Անվտանգություն",
  "7. Rights and clinic responsibilities": "7. Իրավունքները և կլինիկայի պարտականությունները",
  "8. International processing and changes": "8. Միջազգային մշակում և փոփոխություններ",
  "1. Agreement and eligibility": "1. Համաձայնություն և իրավասություն",
  "2. Access and subscription": "2. Մուտք և բաժանորդագրություն",
  "3. Clinical responsibility": "3. Կլինիկական պատասխանատվություն",
  "4. Clinic obligations": "4. Կլինիկայի պարտականությունները",
  "5. Acceptable use": "5. Թույլատրելի օգտագործում",
  "6. Messaging and third parties": "6. Հաղորդագրություններ և երրորդ կողմեր",
  "7. Availability, suspension and termination": "7. Հասանելիություն, կասեցում և դադարեցում",
  "8. Intellectual property and feedback": "8. Մտավոր սեփականություն և արձագանք",
  "9. Liability and law": "9. Պատասխանատվություն և կիրառելի իրավունք",
  "1. Current storage": "1. Ներկայում օգտագործվող պահոցը",
  "2. What is not used": "2. Ինչ չի օգտագործվում",
  "3. Your controls": "3. Ձեր վերահսկման հնարավորությունները",
  "1. Approved payment flow": "1. Հաստատված վճարման ընթացքը",
  "2. Price, currency and activation": "2. Գին, արժույթ և ակտիվացում",
  "3. Cancellations and refunds": "3. Չեղարկումներ և վերադարձներ",
  "4. Expiry and renewal": "4. Ժամկետի ավարտ և երկարաձգում",
  "1. Qualified professional review required": "1. Պահանջվում է որակավորված մասնագետի վերանայում",
  "2. Known limitations": "2. Հայտնի սահմանափակումներ",
  "3. Not for emergencies or autonomous care": "3. Նախատեսված չէ շտապ դեպքերի կամ ինքնավար բուժօգնության համար",
  "4. Follow-up and messaging": "4. Հետագա վերահսկում և հաղորդագրություններ",
};

const LEGAL_RU: Dict = {
  "The rules governing access to and use of the Teta2 clinical software platform.": "Правила доступа к клинической программной платформе Teta2 и ее использования.",
  "How Teta2 handles clinic applications, account information, patient records, OPG images and clinical workflow data.": "Как Teta2 обрабатывает заявки клиник, данные учетных записей, карты пациентов, изображения OPG и данные клинического рабочего процесса.",
  "A precise list of what the current Teta2 frontend stores in your browser.": "Точный перечень того, что текущий фронтенд Teta2 хранит в вашем браузере.",
  "How the current clinic subscription payment process actually works.": "Как фактически устроен текущий процесс оплаты подписки клиники.",
  "The boundaries of Teta2's OPG analysis and follow-up assistance.": "Границы использования анализа OPG и помощи Teta2 в последующем наблюдении.",
  "1. Scope and roles": "1. Область действия и роли",
  "2. Information processed": "2. Обрабатываемая информация",
  "3. Purposes and legal grounds": "3. Цели и правовые основания",
  "4. Infrastructure and recipients": "4. Инфраструктура и получатели данных",
  "5. Retention": "5. Срок хранения",
  "6. Security": "6. Безопасность",
  "7. Rights and clinic responsibilities": "7. Права и обязанности клиники",
  "8. International processing and changes": "8. Международная обработка и изменения",
  "1. Agreement and eligibility": "1. Согласие и правомочность",
  "2. Access and subscription": "2. Доступ и подписка",
  "3. Clinical responsibility": "3. Клиническая ответственность",
  "4. Clinic obligations": "4. Обязанности клиники",
  "5. Acceptable use": "5. Допустимое использование",
  "6. Messaging and third parties": "6. Сообщения и третьи стороны",
  "7. Availability, suspension and termination": "7. Доступность, приостановление и прекращение",
  "8. Intellectual property and feedback": "8. Интеллектуальная собственность и обратная связь",
  "9. Liability and law": "9. Ответственность и применимое право",
  "1. Current storage": "1. Используемое хранилище",
  "2. What is not used": "2. Что не используется",
  "3. Your controls": "3. Ваши настройки",
  "1. Approved payment flow": "1. Утвержденный процесс оплаты",
  "2. Price, currency and activation": "2. Цена, валюта и активация",
  "3. Cancellations and refunds": "3. Отмена и возврат средств",
  "4. Expiry and renewal": "4. Окончание срока и продление",
  "1. Qualified professional review required": "1. Требуется проверка квалифицированным специалистом",
  "2. Known limitations": "2. Известные ограничения",
  "3. Not for emergencies or autonomous care": "3. Не для экстренной или автономной медицинской помощи",
  "4. Follow-up and messaging": "4. Последующее наблюдение и сообщения",
};

function langNow(): Lang {
  const value = localStorage.getItem("teta2-product-language") ?? localStorage.getItem("teta2-v4-language") ?? document.documentElement.lang;
  if (value.toLowerCase().startsWith("hy")) return "hy";
  if (value.toLowerCase().startsWith("ru")) return "ru";
  return "en";
}

function titleCaseStatus(value: string): string {
  return value.replaceAll("_", " ").toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase());
}

function dynamic(source: string, lang: Lang): string | null {
  let m = source.match(/^Analysis status:\s*(.+)$/);
  if (m) return lang === "hy" ? `Վերլուծության կարգավիճակ՝ ${STATUS_HY[m[1]] ?? m[1]}` : lang === "ru" ? `Статус анализа: ${STATUS_RU[m[1]] ?? m[1]}` : source;
  m = source.match(/^Review recommended for (\d+) teeth?, but generation is available now\.$/);
  if (m) return lang === "hy" ? `Խորհուրդ է տրվում վերանայել ${m[1]} ատամ, սակայն պլանը կարելի է ստեղծել արդեն հիմա։` : lang === "ru" ? `Рекомендуется проверить ${m[1]} зуб(а), но план можно создать уже сейчас.` : source;
  m = source.match(/^Sequential follow-up plan generated for (\d+) pathological teeth?\.$/);
  if (m) return lang === "hy" ? `Ստեղծվել է հերթական հետագա վերահսկման պլան՝ ${m[1]} պաթոլոգիական ատամի համար։` : lang === "ru" ? `Создан последовательный план наблюдения для ${m[1]} зуб(а) с патологическими изменениями.` : source;
  m = source.match(/^Saved tooth (\d+)\.$/);
  if (m) return lang === "hy" ? `Պահպանվել է ${m[1]} ատամի պլանը։` : lang === "ru" ? `План по зубу ${m[1]} сохранен.` : source;
  m = source.match(/^Tooth (\d+)$/);
  if (m) return lang === "hy" ? `Ատամ ${m[1]}` : lang === "ru" ? `Зуб ${m[1]}` : source;
  m = source.match(/^Outcome recorded (.+)$/);
  if (m) return lang === "hy" ? `Արդյունքը գրանցվել է՝ ${m[1]}` : lang === "ru" ? `Результат зафиксирован: ${m[1]}` : source;
  return null;
}

function status(source: string, lang: Lang): string | null {
  const normalized = titleCaseStatus(source);
  if (lang === "hy") return STATUS_HY[normalized] ?? null;
  if (lang === "ru") return STATUS_RU[normalized] ?? null;
  return null;
}

function shouldSkip(element: Element | null): boolean {
  if (!element) return false;
  if (element.closest(PROTECTED_PUBLIC)) return true;
  if (element.closest(".enhanced-thread article p")) return true;
  return false;
}

function translate(source: string, lang: Lang, element: Element | null): string {
  const trimmed = source.trim();
  if (!trimmed || lang === "en" || shouldSkip(element)) return source;
  const dict = lang === "hy" ? HY : RU;
  const page = lang === "hy" ? PAGE_HY : PAGE_RU;
  const legal = lang === "hy" ? LEGAL_HY : LEGAL_RU;
  let result = dict[trimmed] ?? page[trimmed] ?? legal[trimmed] ?? dynamic(trimmed, lang) ?? trimmed;

  if (element?.closest(".clinical-pill, .case-status, .clinic-status, .conversation-appointment > b, .enhanced-thread article > small")) {
    result = status(trimmed, lang) ?? result;
  }

  if (element?.closest(".deck2") && result === trimmed) {
    const rules = lang === "hy" ? PAGE_RULES_HY : PAGE_RULES_RU;
    for (const [pattern, replacement] of rules) result = result.replace(pattern, replacement);
  }

  if (result === trimmed) return source;
  const start = source.indexOf(trimmed);
  return `${source.slice(0, start)}${result}${source.slice(start + trimmed.length)}`;
}

const originals = new WeakMap<Text, string>();
const outputs = new WeakMap<Text, string>();
const attributeOriginals = new WeakMap<Element, Map<string, string>>();
const attributeOutputs = new WeakMap<Element, Map<string, string>>();

function translateText(node: Text, lang: Lang): void {
  const current = node.nodeValue ?? "";
  const previous = outputs.get(node);
  if (!originals.has(node) || (previous !== undefined && current !== previous)) originals.set(node, current);
  const source = originals.get(node) ?? current;
  const next = translate(source, lang, node.parentElement);
  if (next !== current) node.nodeValue = next;
  outputs.set(node, next);
}

function translateAttr(element: Element, name: "placeholder" | "aria-label" | "title", lang: Lang): void {
  const current = element.getAttribute(name);
  if (current == null) return;
  let sourceMap = attributeOriginals.get(element);
  if (!sourceMap) { sourceMap = new Map(); attributeOriginals.set(element, sourceMap); }
  let outputMap = attributeOutputs.get(element);
  if (!outputMap) { outputMap = new Map(); attributeOutputs.set(element, outputMap); }
  const previous = outputMap.get(name);
  if (!sourceMap.has(name) || (previous !== undefined && current !== previous)) sourceMap.set(name, current);
  const source = sourceMap.get(name) ?? current;
  const next = translate(source, lang, element);
  if (next !== current) element.setAttribute(name, next);
  outputMap.set(name, next);
}

function apply(root: Node, lang: Lang): void {
  if (root.nodeType === Node.TEXT_NODE) { translateText(root as Text, lang); return; }
  if (!(root instanceof Element) && root !== document.body) return;
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  let node = walker.nextNode();
  while (node) { translateText(node as Text, lang); node = walker.nextNode(); }
  const scope = root as Element | HTMLElement;
  const elements = root instanceof Element ? [root, ...Array.from(root.querySelectorAll("[placeholder],[aria-label],[title]"))] : Array.from(scope.querySelectorAll("[placeholder],[aria-label],[title]"));
  for (const element of elements) {
    translateAttr(element, "placeholder", lang);
    translateAttr(element, "aria-label", lang);
    translateAttr(element, "title", lang);
  }
}

function refreshAll(): void {
  window.requestAnimationFrame(() => apply(document.body, langNow()));
}

/** Text-only localization quality pass. No layout, styles, data, permissions or workflow logic are changed. */
export function FrontendLocaleQuality() {
  useEffect(() => {
    refreshAll();
    const observer = new MutationObserver((records) => {
      const lang = langNow();
      for (const record of records) {
        if (record.type === "characterData") translateText(record.target as Text, lang);
        for (const node of Array.from(record.addedNodes)) apply(node, lang);
        if (record.type === "attributes" && record.target instanceof Element) {
          const name = record.attributeName;
          if (name === "placeholder" || name === "aria-label" || name === "title") translateAttr(record.target, name, lang);
        }
      }
    });
    observer.observe(document.body, { childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ["placeholder", "aria-label", "title"] });
    window.addEventListener("teta2-language-change", refreshAll);
    window.addEventListener("popstate", refreshAll);
    return () => {
      observer.disconnect();
      window.removeEventListener("teta2-language-change", refreshAll);
      window.removeEventListener("popstate", refreshAll);
    };
  }, []);
  return null;
}
