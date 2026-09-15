import { useEffect } from "react";

export type DashboardLang = "en" | "hy" | "ru";
type Dict = Record<string, string>;

const DASHBOARD_SCOPE = [
  ".care-shell",
  ".clinic-shell",
  ".care-integrated-workspace",
  ".care-integrated-body",
  ".account-settings",
  ".subscription-lock-layer",
  ".subscription-confirm-layer",
  ".subscription-upgrade-panel",
].join(",");

const SKIP_SCOPE = [
  ".care-bubbles article p",
  ".enhanced-thread article p",
  ".care-transcript article p",
  ".conversation-message-body",
  ".patient-message",
  "textarea",
  "input",
  "[contenteditable='true']",
  ".t2-navbar",
  ".t2-footer",
  ".product-home-hero",
  ".deck2",
  ".pav2-access-shell",
].join(",");

const HY: Dict = {
  "Open navigation": "Բացել նավիգացիան",
  "Close navigation": "Փակել նավիգացիան",
  "Clinical workspace": "Կլինիկական աշխատանքային միջավայր",
  "Alerts": "Ծանուցումներ",
  "Dashboard": "Գլխավոր վահանակ",
  "Patients & records": "Պացիենտներ և քարտեր",
  "OPG + AI": "ՕՊԳ + ԱԲ",
  "Follow-up plans": "Հետագա հսկողության պլաններ",
  "AI conversations": "ԱԲ զրույցներ",
  "Appointments": "Այցեր",
  "Working hours": "Աշխատանքային ժամեր",
  "Settings": "Կարգավորումներ",
  "Subscription": "Բաժանորդագրություն",
  "No expiry": "Առանց ժամկետի",
  "Today": "Այսօր",
  "Awaiting your approval": "Սպասում է ձեր հաստատմանը",
  "Active care plans": "Ակտիվ խնամքի պլաններ",
  "Active AI conversations": "Ակտիվ ԱԲ զրույցներ",
  "Follow-ups due": "Ժամկետը հասած հետագա հսկողություններ",
  "Retry": "Կրկին փորձել",
  "Select patient": "Ընտրել պացիենտ",
  "Select a patient": "Ընտրել պացիենտ",
  "New patient": "Նոր պացիենտ",
  "Save": "Պահպանել",
  "Cancel": "Չեղարկել",
  "Upload OPG": "Վերբեռնել ՕՊԳ",
  "Run AI analysis": "Գործարկել ԱԲ վերլուծությունը",
  "Approve plan & start outreach": "Հաստատել պլանը և կապ հաստատել պացիենտի հետ",
  "Approve appointment": "Հաստատել այցը",
  "Request another time": "Առաջարկել այլ ժամ",
  "Your clinical day, in one place.": "Ձեր կլինիկական օրը՝ մեկ տեղում։",
  "Ready for your clinical decisions": "Պատրաստ է ձեր կլինիկական որոշումներին",
  "Next clinical actions": "Հաջորդ կլինիկական գործողությունները",
  "Confirm or request another time": "Հաստատել կամ առաջարկել այլ ժամ",
  "TETA2 AI": "TETA2 ԱԲ",
  "TETA2 · CLINICAL ORCHESTRATION": "TETA2 · ԿԼԻՆԻԿԱԿԱՆ ԿԱՌԱՎԱՐՈՒՄ",
  "AUTONOMOUS": "ԻՆՔՆԱՎԱՐ",
  "AI Care": "ԱԲ խնամք",
  "AI Messages": "ԱԲ հաղորդագրություններ",
  "AI Settings": "ԱԲ կարգավորումներ",
  "AI care workflow": "ԱԲ-ով կառավարվող խնամքի գործընթաց",
  "Check-up appointments": "Ստուգայցերի ամրագրումներ",
  "Patient AI conversations": "Պացիենտների ԱԲ զրույցներ",
  "AI schedule & memory": "ԱԲ ժամանակացույց և հիշողություն",
  "You control clinical decisions. Teta2 coordinates the workflow, outreach, conversation and booking.": "Կլինիկական որոշումները վերահսկում եք դուք։ Teta2-ը համակարգում է գործընթացը, կապը պացիենտի հետ, զրույցն ու ամրագրումը։",
  "AI LIVE": "ԱԲ ԱԿՏԻՎ",
  "AI flow": "ԱԲ գործընթաց",
  "Messages": "Հաղորդագրություններ",
  "AI settings": "ԱԲ կարգավորումներ",
  "LIVE CLINICAL LOOP": "ԱԿՏԻՎ ԿԼԻՆԻԿԱԿԱՆ ՇՂԹԱ",
  "Create the patient. Upload the OPG. Teta2 takes it from there.": "Ստեղծեք պացիենտի քարտը, վերբեռնեք ՕՊԳ-ն, իսկ հետագա գործընթացը կկազմակերպի Teta2-ը։",
  "After analysis, AI builds a tooth-level care plan. You confirm the clinical findings; then follow-up, WhatsApp conversation, slot negotiation and booking continue automatically.": "Վերլուծությունից հետո ԱԲ-ն կազմում է յուրաքանչյուր ատամի խնամքի պլանը։ Դուք հաստատում եք կլինիկական արդյունքները, որից հետո հետագա հսկողությունը, WhatsApp զրույցը, ժամի համաձայնեցումն ու ամրագրումը շարունակվում են ավտոմատ։",
  "Clinical outreach stays behind the clinician-review gate.": "Պացիենտին կլինիկական հաղորդագրություն չի ուղարկվում մինչև բժշկի հաստատումը։",
  "Active patient": "Ակտիվ պացիենտ",
  "Upload OPG & analyze": "Վերբեռնել ՕՊԳ և վերլուծել",
  "Create patient": "Ստեղծել պացիենտ",
  "AI care plans": "ԱԲ խնամքի պլաններ",
  "Findings contacted": "Կապ հաստատված արդյունքներ",
  "Confirmed bookings": "Հաստատված ամրագրումներ",
  "AUTONOMOUS CARE LOOP": "ԽՆԱՄՔԻ ԱՎՏՈՄԱՏ ՇՂԹԱ",
  "From OPG to confirmed check-up": "ՕՊԳ-ից մինչև հաստատված ստուգայց",
  "AI analysis": "ԱԲ վերլուծություն",
  "Clinician review": "Բժշկի վերանայում",
  "Slot negotiation": "Ժամի համաձայնեցում",
  "Booking": "Ամրագրում",
  "ACTIVE CLINICAL RECORD": "ԱԿՏԻՎ ԿԼԻՆԻԿԱԿԱՆ ՔԱՐՏ",
  "No WhatsApp number": "WhatsApp համար նշված չէ",
  "Open OPG workspace": "Բացել ՕՊԳ աշխատանքային միջավայրը",
  "AI CARE PLANS": "ԱԲ ԽՆԱՄՔԻ ՊԼԱՆՆԵՐ",
  "LATEST STATE": "ՎԵՐՋԻՆ ԿԱՐԳԱՎԻՃԱԿ",
  "NEXT ACTION": "ՀԱՋՈՐԴ ԳՈՐԾՈՂՈՒԹՅՈՒՆ",
  "Awaiting OPG": "Սպասում է ՕՊԳ-ին",
  "AI monitoring": "ԱԲ հսկողություն",
  "Latest AI care plans": "Վերջին ԱԲ խնամքի պլանները",
  "Review findings": "Վերանայել արդյունքները",
  "Day": "Օր",
  "Week": "Շաբաթ",
  "Tooth": "Ատամ",
  "Change time": "Փոխել ժամը",
  "No appointments in this period.": "Այս ժամանակահատվածում այցեր չկան։",
  "TETA2 · RESCHEDULE": "TETA2 · ԺԱՄԻ ՓՈՓՈԽՈՒԹՅՈՒՆ",
  "Ask AI to renegotiate the appointment": "Հանձնարարել ԱԲ-ին համաձայնեցնել այցի նոր ժամը",
  "Doctor-preferred new time": "Բժշկի նախընտրած նոր ժամը",
  "Instruction for AI": "Հրահանգ ԱԲ-ի համար",
  "If unavailable, offer next Tuesday afternoon": "Եթե այս ժամը հասանելի չէ, առաջարկել հաջորդ երեքշաբթի կեսօրից հետո",
  "Start rescheduling conversation": "Սկսել ժամի փոփոխության զրույցը",
  "Patient conversations": "Պացիենտների զրույցներ",
  "No Care conversation yet.": "Խնամքի վերաբերյալ զրույց դեռ չկա։",
  "Select a branch.": "Ընտրեք մասնաճյուղ։",
  "CLINIC MEMORY · BOOKING POLICY": "ԿԼԻՆԻԿԱՅԻ ՀԻՇՈՂՈՒԹՅՈՒՆ · ԱՄՐԱԳՐՄԱՆ ԿԱՆՈՆՆԵՐ",
  "Clinic schedule & AI booking memory": "Կլինիկայի ժամանակացույց և ԱԲ ամրագրման հիշողություն",
  "These rules are persistent context for every Care conversation and appointment offer.": "Այս կանոնները պահպանվում են և կիրառվում յուրաքանչյուր խնամքի զրույցի ու այցի առաջարկի ժամանակ։",
  "Branch": "Մասնաճյուղ",
  "Timezone": "Ժամային գոտի",
  "Clinic opens": "Կլինիկայի բացման ժամը",
  "Clinic closes": "Կլինիկայի փակման ժամը",
  "Check-up duration": "Ստուգայցի տևողություն",
  "Slot interval": "Ժամային միջակայք",
  "Appointment buffer": "Այցերի միջև ընդմիջում",
  "Minimum notice": "Նվազագույն նախազգուշացում",
  "Booking horizon": "Ամրագրման առավելագույն ժամկետ",
  "Working days": "Աշխատանքային օրեր",
  "Booking instructions for the AI": "Ամրագրման հրահանգներ ԱԲ-ի համար",
  "e.g. Prefer Wednesday mornings; urgent check-ups may use the final slot": "Օրինակ՝ նախընտրել չորեքշաբթի առավոտները, իսկ հրատապ ստուգայցերի համար օգտագործել վերջին ազատ ժամը",
  "Automatic Care plan": "Խնամքի ավտոմատ պլան",
  "Prepare after OPG analysis": "Պատրաստել ՕՊԳ վերլուծությունից հետո",
  "Automatic WhatsApp after review": "Բժշկի վերանայումից հետո ավտոմատ WhatsApp հաղորդագրություն",
  "Only clinician-confirmed findings": "Միայն բժշկի հաստատած արդյունքների համար",
  "Attach tooth crop": "Կցել ատամի հատվածի պատկերը",
  "Send the relevant tooth image": "Ուղարկել համապատասխան ատամի պատկերը",
  "Save AI automation rules": "Պահպանել ԱԲ ավտոմատացման կանոնները",
  "NEW CLINICAL RECORD · START CARE LOOP": "ՆՈՐ ԿԼԻՆԻԿԱԿԱՆ ՔԱՐՏ · ՍԿՍԵԼ ԽՆԱՄՔԻ ՇՂԹԱՆ",
  "Create the patient’s clinical record": "Ստեղծել պացիենտի կլինիկական քարտը",
  "Use international format for the WhatsApp number. Teta2 also uses it to choose the patient’s communication language.": "WhatsApp համարը նշեք միջազգային ձևաչափով։ Teta2-ն այն օգտագործում է նաև պացիենտի հաղորդակցության լեզուն ընտրելու համար։",
  "This becomes the patient’s clinic-scoped medical record and Care context.": "Այս տվյալները դառնում են տվյալ կլինիկայում պացիենտի բժշկական քարտն ու խնամքի համատեքստը։",
  "Patient number": "Պացիենտի համար",
  "Date of birth": "Ծննդյան ամսաթիվ",
  "First name": "Անուն",
  "Last name": "Ազգանուն",
  "Sex": "Սեռ",
  "Female": "Իգական",
  "Male": "Արական",
  "Other / unspecified": "Այլ / չնշված",
  "Phone": "Հեռախոս",
  "Email": "Էլ․ փոստ",
  "Create clinical record": "Ստեղծել կլինիկական քարտ",
  "min": "րոպե",
  "days": "օր",
  "Mon": "Երկ",
  "Tue": "Երք",
  "Wed": "Չրք",
  "Thu": "Հնգ",
  "Fri": "Ուրբ",
  "Sat": "Շբթ",
  "Sun": "Կիր",

  /* Freemium / subscription dashboard */
  "Free · 24 hours": "Անվճար · 24 ժամ",
  "Free ended": "Անվճար շրջանն ավարտվել է",
  "Premium · approval pending": "Պրեմիում · հաստատման սպասում",
  "TETA2 PREMIUM": "TETA2 ՊՐԵՄԻՈՒՄ",
  "Unlock the full clinic workspace for 30 days": "Բացեք կլինիկայի ամբողջ աշխատանքային միջավայրը 30 օրով",
  "Unlimited patients, OPGs and tooth follow-up with your existing clinic history preserved.": "Անսահմանափակ պացիենտներ, ՕՊԳ-ներ և ատամների հետագա հսկողություն՝ պահպանելով կլինիկայի ամբողջ պատմությունը։",
  "Waiting for approval": "Սպասում է հաստատման",
  "Upgrade to Premium": "Անցնել Պրեմիում փաթեթի",
  "Premium is active": "Պրեմիում փաթեթն ակտիվ է",
  "Your existing clinic workspace and history stay continuous.": "Կլինիկայի նույն աշխատանքային միջավայրն ու ամբողջ պատմությունը պահպանվում են։",
  "FREE ACCESS ENDED": "ԱՆՎՃԱՐ ՄՈՒՏՔՆ ԱՎԱՐՏՎԵԼ Է",
  "Your 24-hour Free plan has finished.": "Ձեր 24-ժամյա անվճար փաթեթն ավարտվել է։",
  "Your patients, OPGs, follow-up history, conversations and settings are still safely stored. Activate Premium to continue using Teta2 for the next 30 days.": "Պացիենտների տվյալները, ՕՊԳ-ները, հետագա հսկողության պատմությունը, զրույցներն ու կարգավորումները անվտանգ պահպանված են։ Ակտիվացրեք Պրեմիումը՝ Teta2-ը ևս 30 օր օգտագործելու համար։",
  "✓ Same dashboard": "✓ Նույն վահանակը",
  "✓ Same clinic data": "✓ Նույն կլինիկայի տվյալները",
  "✓ Unlimited Premium usage": "✓ Անսահմանափակ Պրեմիում օգտագործում",
  "Go to Settings & activate Premium": "Բացել կարգավորումները և ակտիվացնել Պրեմիումը",
  "PAYMENT REVIEW": "ՎՃԱՐՄԱՆ ՍՏՈՒԳՈՒՄ",
  "Premium activation is being confirmed.": "Պրեմիում ակտիվացումը ստուգվում է։",
  "Your request has been sent to the Teta2 administration panel. Approval normally takes between": "Ձեր հայտը ուղարկվել է Teta2-ի ադմինիստրատորի վահանակ։ Հաստատումը սովորաբար տևում է",
  "1 and 6 hours": "1-ից 6 ժամ",
  "You can leave this page open. The dashboard will unlock automatically after approval.": "Կարող եք այս էջը բաց թողնել։ Հաստատումից հետո վահանակն ավտոմատ կբացվի։",
  "CONFIRM UPGRADE": "ՀԱՍՏԱՏԵԼ ՓԱԹԵԹԻ ԲԱՐՁՐԱՑՈՒՄԸ",
  "Activate Teta2 Premium": "Ակտիվացնել Teta2 Պրեմիումը",
  "30 days of Premium access after admin approval": "Ադմինիստրատորի հաստատումից հետո՝ 30 օր Պրեմիում հասանելիություն",
  "No patient or OPG limits from the Free plan": "Անվճար փաթեթի պացիենտների և ՕՊԳ-ների սահմանափակումները հանվում են",
  "Your existing dashboard and all clinic history remain unchanged": "Նույն վահանակն ու կլինիկայի ամբողջ պատմությունը մնում են անփոփոխ",
  "Confirm & continue": "Հաստատել և շարունակել",
  "Submitting…": "Ուղարկվում է…",

  /* Native replacements for hybrid Armenian source strings */
  "Teta2 · կլինիկական follow-up workspace": "Teta2 · կլինիկական հետագա հսկողության աշխատանքային միջավայր",
  "Ակտիվ care պլաններ": "Ակտիվ խնամքի պլաններ",
  "Ժամկետը հասած follow-up": "Ժամկետը հասած հետագա հսկողություններ",
  "Care API-ն դեռ տեղադրված չէ միացված backend-ում։": "Հետագա հսկողության ծառայությունը դեռ հասանելի չէ միացված սերվերում։",
  "Վերանայեք և փոխեք ատամային follow-up պլանը մինչև outreach-ի հաստատումը։": "Վերանայեք և ճշգրտեք ատամների հետագա հսկողության պլանը՝ մինչև պացիենտի հետ կապ հաստատելը։",
  "Հաստատել պլանը և սկսել outreach": "Հաստատել պլանը և կապ հաստատել պացիենտի հետ",
  "AI care պլան": "ԱԲ խնամքի պլան",
  "AI զրույց": "ԱԲ զրույց",
  "AI վերլուծություն": "ԱԲ վերլուծություն",
  "AI վերահսկում": "ԱԲ հսկողություն",
  "Բացել OPG workspace": "Բացել ՕՊԳ աշխատանքային միջավայրը",
  "Վերջին AI Care պլանները": "Վերջին ԱԲ խնամքի պլանները",
};

const RU: Dict = {
  "Open navigation": "Открыть навигацию",
  "Close navigation": "Закрыть навигацию",
  "Clinical workspace": "Клиническое рабочее пространство",
  "Alerts": "Уведомления",
  "Dashboard": "Главная панель",
  "Patients & records": "Пациенты и карты",
  "OPG + AI": "ОПТГ + ИИ",
  "Follow-up plans": "Планы последующего наблюдения",
  "AI conversations": "Диалоги с ИИ",
  "Appointments": "Приемы",
  "Working hours": "Рабочее время",
  "Settings": "Настройки",
  "Subscription": "Подписка",
  "No expiry": "Без ограничения срока",
  "Today": "Сегодня",
  "Awaiting your approval": "Ожидают вашего подтверждения",
  "Active care plans": "Активные планы наблюдения",
  "Active AI conversations": "Активные диалоги с ИИ",
  "Follow-ups due": "Наблюдения к выполнению",
  "Retry": "Повторить",
  "Select patient": "Выберите пациента",
  "Select a patient": "Выберите пациента",
  "New patient": "Новый пациент",
  "Save": "Сохранить",
  "Cancel": "Отмена",
  "Upload OPG": "Загрузить ОПТГ",
  "Run AI analysis": "Запустить анализ ИИ",
  "Approve plan & start outreach": "Подтвердить план и начать связь с пациентом",
  "Approve appointment": "Подтвердить прием",
  "Request another time": "Предложить другое время",
  "Your clinical day, in one place.": "Весь клинический день — в одном месте.",
  "Ready for your clinical decisions": "Готов к вашим клиническим решениям",
  "Next clinical actions": "Следующие клинические действия",
  "Confirm or request another time": "Подтвердить или предложить другое время",
  "TETA2 AI": "TETA2 ИИ",
  "TETA2 · CLINICAL ORCHESTRATION": "TETA2 · КЛИНИЧЕСКАЯ КООРДИНАЦИЯ",
  "AUTONOMOUS": "АВТОМАТИЗАЦИЯ",
  "AI Care": "ИИ-наблюдение",
  "AI Messages": "Сообщения ИИ",
  "AI Settings": "Настройки ИИ",
  "AI care workflow": "Процесс наблюдения с ИИ",
  "Check-up appointments": "Записи на контрольный прием",
  "Patient AI conversations": "Диалоги ИИ с пациентами",
  "AI schedule & memory": "Расписание и память ИИ",
  "You control clinical decisions. Teta2 coordinates the workflow, outreach, conversation and booking.": "Клинические решения принимаете вы. Teta2 координирует рабочий процесс, связь с пациентом, диалог и запись на прием.",
  "AI LIVE": "ИИ АКТИВЕН",
  "AI flow": "Процесс ИИ",
  "Messages": "Сообщения",
  "AI settings": "Настройки ИИ",
  "LIVE CLINICAL LOOP": "АКТИВНЫЙ КЛИНИЧЕСКИЙ ЦИКЛ",
  "Create the patient. Upload the OPG. Teta2 takes it from there.": "Создайте карту пациента и загрузите ОПТГ. Дальнейший процесс организует Teta2.",
  "After analysis, AI builds a tooth-level care plan. You confirm the clinical findings; then follow-up, WhatsApp conversation, slot negotiation and booking continue automatically.": "После анализа ИИ формирует план наблюдения по каждому зубу. Вы подтверждаете клинические результаты, после чего последующее наблюдение, диалог в WhatsApp, согласование времени и запись продолжаются автоматически.",
  "Clinical outreach stays behind the clinician-review gate.": "Клинические сообщения пациенту отправляются только после подтверждения врачом.",
  "Active patient": "Активный пациент",
  "Upload OPG & analyze": "Загрузить ОПТГ и проанализировать",
  "Create patient": "Создать пациента",
  "AI care plans": "Планы наблюдения ИИ",
  "Findings contacted": "Результаты с начатой связью",
  "Confirmed bookings": "Подтвержденные записи",
  "AUTONOMOUS CARE LOOP": "АВТОМАТИЗИРОВАННЫЙ ЦИКЛ НАБЛЮДЕНИЯ",
  "From OPG to confirmed check-up": "От ОПТГ до подтвержденного контрольного приема",
  "AI analysis": "Анализ ИИ",
  "Clinician review": "Проверка врачом",
  "Slot negotiation": "Согласование времени",
  "Booking": "Запись на прием",
  "ACTIVE CLINICAL RECORD": "АКТИВНАЯ КЛИНИЧЕСКАЯ КАРТА",
  "No WhatsApp number": "Номер WhatsApp не указан",
  "Open OPG workspace": "Открыть рабочее пространство ОПТГ",
  "AI CARE PLANS": "ПЛАНЫ НАБЛЮДЕНИЯ ИИ",
  "LATEST STATE": "ТЕКУЩИЙ СТАТУС",
  "NEXT ACTION": "СЛЕДУЮЩЕЕ ДЕЙСТВИЕ",
  "Awaiting OPG": "Ожидается ОПТГ",
  "AI monitoring": "Наблюдение ИИ",
  "Latest AI care plans": "Последние планы наблюдения ИИ",
  "Review findings": "Проверить результаты",
  "Day": "День",
  "Week": "Неделя",
  "Tooth": "Зуб",
  "Change time": "Изменить время",
  "No appointments in this period.": "На этот период записей нет.",
  "TETA2 · RESCHEDULE": "TETA2 · ИЗМЕНЕНИЕ ВРЕМЕНИ",
  "Ask AI to renegotiate the appointment": "Поручить ИИ согласовать новое время приема",
  "Doctor-preferred new time": "Предпочтительное время врача",
  "Instruction for AI": "Инструкция для ИИ",
  "If unavailable, offer next Tuesday afternoon": "Если время недоступно, предложить следующий вторник после обеда",
  "Start rescheduling conversation": "Начать диалог об изменении времени",
  "Patient conversations": "Диалоги с пациентами",
  "No Care conversation yet.": "Диалога по наблюдению пока нет.",
  "Select a branch.": "Выберите филиал.",
  "CLINIC MEMORY · BOOKING POLICY": "ПАМЯТЬ КЛИНИКИ · ПРАВИЛА ЗАПИСИ",
  "Clinic schedule & AI booking memory": "Расписание клиники и память ИИ для записи",
  "These rules are persistent context for every Care conversation and appointment offer.": "Эти правила сохраняются и используются в каждом диалоге наблюдения и при каждом предложении времени приема.",
  "Branch": "Филиал",
  "Timezone": "Часовой пояс",
  "Clinic opens": "Открытие клиники",
  "Clinic closes": "Закрытие клиники",
  "Check-up duration": "Длительность контрольного приема",
  "Slot interval": "Интервал между временами приема",
  "Appointment buffer": "Буфер между приемами",
  "Minimum notice": "Минимальный срок до приема",
  "Booking horizon": "Горизонт записи",
  "Working days": "Рабочие дни",
  "Booking instructions for the AI": "Инструкции ИИ по записи",
  "e.g. Prefer Wednesday mornings; urgent check-ups may use the final slot": "Например: предпочитать утро среды; срочные контрольные приемы можно ставить в последний свободный интервал",
  "Automatic Care plan": "Автоматический план наблюдения",
  "Prepare after OPG analysis": "Подготавливать после анализа ОПТГ",
  "Automatic WhatsApp after review": "Автоматическое сообщение WhatsApp после проверки",
  "Only clinician-confirmed findings": "Только для результатов, подтвержденных врачом",
  "Attach tooth crop": "Прикреплять фрагмент с зубом",
  "Send the relevant tooth image": "Отправлять изображение соответствующего зуба",
  "Save AI automation rules": "Сохранить правила автоматизации ИИ",
  "NEW CLINICAL RECORD · START CARE LOOP": "НОВАЯ КЛИНИЧЕСКАЯ КАРТА · НАЧАТЬ ЦИКЛ НАБЛЮДЕНИЯ",
  "Create the patient’s clinical record": "Создать клиническую карту пациента",
  "Use international format for the WhatsApp number. Teta2 also uses it to choose the patient’s communication language.": "Укажите номер WhatsApp в международном формате. Teta2 также использует его для выбора языка общения с пациентом.",
  "This becomes the patient’s clinic-scoped medical record and Care context.": "Эти данные становятся медицинской картой пациента и контекстом наблюдения в рамках этой клиники.",
  "Patient number": "Номер пациента",
  "Date of birth": "Дата рождения",
  "First name": "Имя",
  "Last name": "Фамилия",
  "Sex": "Пол",
  "Female": "Женский",
  "Male": "Мужской",
  "Other / unspecified": "Другое / не указано",
  "Phone": "Телефон",
  "Email": "Эл. почта",
  "Create clinical record": "Создать клиническую карту",
  "min": "мин",
  "days": "дней",
  "Mon": "Пн",
  "Tue": "Вт",
  "Wed": "Ср",
  "Thu": "Чт",
  "Fri": "Пт",
  "Sat": "Сб",
  "Sun": "Вс",

  /* Freemium / subscription dashboard */
  "Free · 24 hours": "Бесплатно · 24 часа",
  "Free ended": "Бесплатный период завершен",
  "Premium · approval pending": "Премиум · ожидает подтверждения",
  "TETA2 PREMIUM": "TETA2 ПРЕМИУМ",
  "Unlock the full clinic workspace for 30 days": "Откройте полный функционал клиники на 30 дней",
  "Unlimited patients, OPGs and tooth follow-up with your existing clinic history preserved.": "Неограниченное число пациентов, ОПТГ и наблюдений по зубам с сохранением всей истории клиники.",
  "Waiting for approval": "Ожидает подтверждения",
  "Upgrade to Premium": "Перейти на Премиум",
  "Premium is active": "Премиум активен",
  "Your existing clinic workspace and history stay continuous.": "Текущее рабочее пространство и вся история клиники сохраняются.",
  "FREE ACCESS ENDED": "БЕСПЛАТНЫЙ ДОСТУП ЗАВЕРШЕН",
  "Your 24-hour Free plan has finished.": "Ваш 24-часовой бесплатный период завершен.",
  "Your patients, OPGs, follow-up history, conversations and settings are still safely stored. Activate Premium to continue using Teta2 for the next 30 days.": "Пациенты, ОПТГ, история наблюдения, диалоги и настройки надежно сохранены. Активируйте Премиум, чтобы продолжить работу с Teta2 еще 30 дней.",
  "✓ Same dashboard": "✓ Та же панель",
  "✓ Same clinic data": "✓ Те же данные клиники",
  "✓ Unlimited Premium usage": "✓ Неограниченное использование Премиум",
  "Go to Settings & activate Premium": "Перейти в настройки и активировать Премиум",
  "PAYMENT REVIEW": "ПРОВЕРКА ОПЛАТЫ",
  "Premium activation is being confirmed.": "Активация Премиум подтверждается.",
  "Your request has been sent to the Teta2 administration panel. Approval normally takes between": "Заявка отправлена в административную панель Teta2. Подтверждение обычно занимает",
  "1 and 6 hours": "от 1 до 6 часов",
  "You can leave this page open. The dashboard will unlock automatically after approval.": "Эту страницу можно оставить открытой. После подтверждения панель разблокируется автоматически.",
  "CONFIRM UPGRADE": "ПОДТВЕРДИТЬ ПЕРЕХОД",
  "Activate Teta2 Premium": "Активировать Teta2 Премиум",
  "30 days of Premium access after admin approval": "30 дней Премиум-доступа после подтверждения администратором",
  "No patient or OPG limits from the Free plan": "Без ограничений бесплатного тарифа по пациентам и ОПТГ",
  "Your existing dashboard and all clinic history remain unchanged": "Текущая панель и вся история клиники остаются без изменений",
  "Confirm & continue": "Подтвердить и продолжить",
  "Submitting…": "Отправка…",
};

const ARMENIAN_TO_RU: Dict = {
  "Հերթագրված": "В очереди",
  "Մշակվում է": "Обрабатывается",
  "Ավարտված": "Завершено",
  "Ձախողված": "Ошибка",
  "Սպասող": "Ожидает",
  "Հաստատված": "Подтверждено",
  "Մերժված": "Отклонено",
  "Չվերանայված": "Не проверено",
  "Վերանայված": "Проверено",
  "Պլանավորված": "Запланировано",
  "Ժամկետը հասել է": "Срок наступил",
  "Չեղարկված": "Отменено",
  "Ուղարկված": "Отправлено",
  "Ուղարկվում է": "Отправляется",
  "Կարիես": "Кариес",
  "Խորը կարիես": "Глубокий кариес",
  "Լցոնում": "Пломба",
  "Պսակ": "Коронка",
  "Իմպակցված ատամ": "Ретинированный зуб",
  "Արմատախողովակային բուժում": "Эндодонтическое лечение",
  "Ապիկալ պերիօդոնտիտ": "Апикальный периодонтит",
  "Ոսկրային ռեզորբցիա": "Резорбция костной ткани",
  "Արմատի բեկոր": "Фрагмент корня",
};

const STATUS_HY: Dict = {
  "PENDING APPROVAL": "Սպասում է հաստատման",
  "READY FOR REVIEW": "Պատրաստ է բժշկի վերանայմանը",
  "ACTIVE": "Ակտիվ",
  "PAUSED": "Դադարեցված",
  "COMPLETED": "Ավարտված",
  "FOLLOWUP READY": "Պատրաստ է հետագա հսկողության",
  "WAITING PREVIOUS TOOTH": "Սպասում է նախորդ ատամի փուլին",
  "WAITING NEXT TOOTH": "Սպասում է հաջորդ ատամին",
  "CONTACTED": "Կապ է հաստատվել",
  "BOOKED": "Ամրագրված",
  "PROPOSED": "Առաջարկված",
  "APPROVED": "Հաստատված",
  "CONFIRMED": "Հաստատված",
  "REJECTED": "Մերժված",
  "CANCELLED": "Չեղարկված",
  "TREATED": "Բուժված",
  "ATTENDED NOT TREATED": "Այցելել է՝ առանց բուժման",
  "NO SHOW": "Չի ներկայացել",
  "PENDING": "Սպասման մեջ",
  "SENDING": "Ուղարկվում է",
  "SENT": "Ուղարկված",
  "FAILED": "Չհաջողվեց",
  "QUEUED": "Հերթում",
  "PROCESSING": "Մշակվում է",
  "UNREVIEWED": "Չվերանայված",
  "REVIEWED": "Վերանայված",
};

const STATUS_RU: Dict = {
  "PENDING APPROVAL": "Ожидает подтверждения",
  "READY FOR REVIEW": "Готов к проверке врачом",
  "ACTIVE": "Активен",
  "PAUSED": "Приостановлен",
  "COMPLETED": "Завершен",
  "FOLLOWUP READY": "Готов к наблюдению",
  "WAITING PREVIOUS TOOTH": "Ожидает завершения предыдущего зуба",
  "WAITING NEXT TOOTH": "Ожидает следующего зуба",
  "CONTACTED": "Связь установлена",
  "BOOKED": "Записан",
  "PROPOSED": "Предложено",
  "APPROVED": "Подтверждено",
  "CONFIRMED": "Подтверждено",
  "REJECTED": "Отклонено",
  "CANCELLED": "Отменено",
  "TREATED": "Лечение проведено",
  "ATTENDED NOT TREATED": "Прием состоялся без лечения",
  "NO SHOW": "Не явился",
  "PENDING": "Ожидает",
  "SENDING": "Отправляется",
  "SENT": "Отправлено",
  "FAILED": "Ошибка",
  "QUEUED": "В очереди",
  "PROCESSING": "Обрабатывается",
  "UNREVIEWED": "Не проверено",
  "REVIEWED": "Проверено",
};

const SHORT_HY: Array<[RegExp, string]> = [
  [/\bAI\b/g, "ԱԲ"],
  [/\bOPGs\b/g, "ՕՊԳ-ներ"],
  [/\bOPG\b/g, "ՕՊԳ"],
  [/\bfollow-up\b/gi, "հետագա հսկողություն"],
  [/\bworkspace\b/gi, "աշխատանքային միջավայր"],
  [/\boutreach\b/gi, "կապ պացիենտի հետ"],
  [/\bbackend\b/gi, "սերվեր"],
  [/\bbooking\b/gi, "ամրագրում"],
  [/\bslots?\b/gi, "ժամային միջակայք"],
  [/\breview\b/gi, "վերանայում"],
];

const SHORT_RU: Array<[RegExp, string]> = [
  [/\bAI\b/g, "ИИ"],
  [/\bOPGs\b/g, "ОПТГ"],
  [/\bOPG\b/g, "ОПТГ"],
  [/\bfollow-up\b/gi, "последующее наблюдение"],
  [/\bworkspace\b/gi, "рабочее пространство"],
  [/\boutreach\b/gi, "связь с пациентом"],
  [/\bbackend\b/gi, "сервер"],
  [/\bbooking\b/gi, "запись на прием"],
  [/\bslots?\b/gi, "время приема"],
  [/\breview\b/gi, "проверка"],
];

function languageNow(): DashboardLang {
  const value = localStorage.getItem("teta2-product-language") ?? localStorage.getItem("teta2-v4-language") ?? document.documentElement.lang;
  if (value.toLowerCase().startsWith("hy")) return "hy";
  if (value.toLowerCase().startsWith("ru")) return "ru";
  return "en";
}

function dynamic(source: string, lang: DashboardLang): string | null {
  let match = source.match(/^(\d+)\s+days left$/i);
  if (match) return lang === "hy" ? `${match[1]} օր մնացել է` : lang === "ru" ? `Осталось ${match[1]} дн.` : source;
  match = source.match(/^Premium · (\d+) days left$/i);
  if (match) return lang === "hy" ? `Պրեմիում · մնացել է ${match[1]} օր` : lang === "ru" ? `Премиум · осталось ${match[1]} дн.` : source;
  match = source.match(/^Free · (\d{1,3}:\d{2}:\d{2})$/i);
  if (match) return lang === "hy" ? `Անվճար · ${match[1]}` : lang === "ru" ? `Бесплатно · ${match[1]}` : source;
  match = source.match(/^(\d+)\s+need review$/i);
  if (match) return lang === "hy" ? `${match[1]}՝ վերանայման ենթակա` : lang === "ru" ? `${match[1]} требуют проверки` : source;
  match = source.match(/^(\d+)\s+tooth finding\(s\)$/i);
  if (match) return lang === "hy" ? `${match[1]} ատամային արդյունք` : lang === "ru" ? `${match[1]} результатов по зубам` : source;
  match = source.match(/^Tooth\s+(\d+)(.*)$/i);
  if (match) return lang === "hy" ? `Ատամ ${match[1]}${match[2]}` : lang === "ru" ? `Зуб ${match[1]}${match[2]}` : source;
  return null;
}

function status(source: string, lang: DashboardLang): string | null {
  const normalized = source.trim().replaceAll("_", " ").replace(/\s+/g, " ").toUpperCase();
  if (lang === "hy") return STATUS_HY[normalized] ?? null;
  if (lang === "ru") return STATUS_RU[normalized] ?? null;
  return null;
}

export function translateDashboardText(source: string, lang: DashboardLang): string {
  if (lang === "en" || !source.trim()) return source;
  const trimmed = source.trim();
  const dict = lang === "hy" ? HY : RU;
  let translated = dict[trimmed] ?? (lang === "ru" ? ARMENIAN_TO_RU[trimmed] : undefined) ?? dynamic(trimmed, lang) ?? status(trimmed, lang) ?? trimmed;

  // Last-resort cleanup is intentionally limited to short UI labels. Long sentences
  // require an exact professional translation above; patient/free-text content is never passed here.
  if (translated === trimmed && trimmed.length <= 80) {
    const rules = lang === "hy" ? SHORT_HY : SHORT_RU;
    for (const [pattern, replacement] of rules) translated = translated.replace(pattern, replacement);
  }
  if (translated === trimmed) return source;
  const start = source.indexOf(trimmed);
  return `${source.slice(0, start)}${translated}${source.slice(start + trimmed.length)}`;
}

function isDashboardElement(element: Element | null): boolean {
  return Boolean(element?.closest(DASHBOARD_SCOPE));
}

function shouldSkip(element: Element | null): boolean {
  return !element || !isDashboardElement(element) || Boolean(element.closest(SKIP_SCOPE));
}

const originals = new WeakMap<Text, string>();
const outputs = new WeakMap<Text, string>();
const attrOriginals = new WeakMap<Element, Map<string, string>>();
const attrOutputs = new WeakMap<Element, Map<string, string>>();

function translateTextNode(node: Text, lang: DashboardLang): void {
  const element = node.parentElement;
  if (shouldSkip(element)) return;
  const current = node.nodeValue ?? "";
  const previous = outputs.get(node);
  if (!originals.has(node) || (previous !== undefined && current !== previous)) originals.set(node, current);
  const source = originals.get(node) ?? current;
  const next = translateDashboardText(source, lang);
  if (next !== current) node.nodeValue = next;
  outputs.set(node, next);
}

function translateAttribute(element: Element, name: "placeholder" | "aria-label" | "title", lang: DashboardLang): void {
  if (shouldSkip(element)) return;
  const current = element.getAttribute(name);
  if (current == null) return;
  let sourceMap = attrOriginals.get(element);
  if (!sourceMap) { sourceMap = new Map(); attrOriginals.set(element, sourceMap); }
  let outputMap = attrOutputs.get(element);
  if (!outputMap) { outputMap = new Map(); attrOutputs.set(element, outputMap); }
  const previous = outputMap.get(name);
  if (!sourceMap.has(name) || (previous !== undefined && current !== previous)) sourceMap.set(name, current);
  const source = sourceMap.get(name) ?? current;
  const next = translateDashboardText(source, lang);
  if (next !== current) element.setAttribute(name, next);
  outputMap.set(name, next);
}

function apply(root: Node, lang: DashboardLang): void {
  if (root.nodeType === Node.TEXT_NODE) { translateTextNode(root as Text, lang); return; }
  if (!(root instanceof Element) && root !== document.body) return;
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  let node = walker.nextNode();
  while (node) { translateTextNode(node as Text, lang); node = walker.nextNode(); }
  const scope = root as Element | HTMLElement;
  const elements = root instanceof Element
    ? [root, ...Array.from(root.querySelectorAll("[placeholder],[aria-label],[title]"))]
    : Array.from(scope.querySelectorAll("[placeholder],[aria-label],[title]"));
  for (const element of elements) {
    translateAttribute(element, "placeholder", lang);
    translateAttribute(element, "aria-label", lang);
    translateAttribute(element, "title", lang);
  }
}

function applyAll(): void {
  window.requestAnimationFrame(() => apply(document.body, languageNow()));
}

/** Native-quality Armenian/Russian pass for authenticated clinic UI only. */
export function DashboardNativeLocale() {
  useEffect(() => {
    let lastLanguage = languageNow();
    applyAll();
    const observer = new MutationObserver((records) => {
      const language = languageNow();
      if (language !== lastLanguage) {
        lastLanguage = language;
        applyAll();
        return;
      }
      for (const record of records) {
        if (record.type === "characterData") translateTextNode(record.target as Text, language);
        for (const node of Array.from(record.addedNodes)) apply(node, language);
        if (record.type === "attributes" && record.target instanceof Element) {
          const name = record.attributeName;
          if (name === "placeholder" || name === "aria-label" || name === "title") translateAttribute(record.target, name, language);
        }
      }
    });
    observer.observe(document.body, {
      childList: true,
      subtree: true,
      characterData: true,
      attributes: true,
      attributeFilter: ["placeholder", "aria-label", "title"],
    });
    window.addEventListener("teta2-language-change", applyAll);
    window.addEventListener("popstate", applyAll);
    return () => {
      observer.disconnect();
      window.removeEventListener("teta2-language-change", applyAll);
      window.removeEventListener("popstate", applyAll);
    };
  }, []);
  return null;
}
