import { useCallback, useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import {
  ArrowLeft,
  Check,
  Clock3,
  Crown,
  LoaderCircle,
  LockKeyhole,
  Mail,
  RefreshCw,
  Sparkles,
  X,
} from "lucide-react";

import {
  api,
  authenticatedRequest,
  clearSession,
  errorMessage,
  hasSession,
} from "../api/client";
import type { CurrentUser } from "../api/types";
import { type DashboardLang } from "./dashboardI18n";
import { useDashboardLanguage } from "./useDashboardLanguage";
import "./subscription-flow.css";

const REVIEW_BODY_CLASS = "subscription-review-active";

const COPY = {
  en: {
    free: "Free",
    free24: "Free · 24 hours",
    freeEnded: "Free ended",
    premium: "Premium",
    daysLeft: (days: number) => `Premium · ${days} days left`,
    pendingShort: "Premium · payment review",
    premiumLabel: "TETA2 PREMIUM",
    unlock: "Unlock the full clinic workspace for 30 days",
    unlimited:
      "Unlimited patients, OPGs and tooth follow-up with your existing clinic history preserved.",
    waiting: "Waiting for payment approval",
    upgrade: "Upgrade to Premium",
    active: "Premium is active",
    activeHelp: "Your existing clinic workspace and history stay continuous.",
    expiredKicker: "FREE ACCESS ENDED",
    expiredTitle: "Your 24-hour Free plan has finished.",
    expiredBody:
      "Your patients, OPGs, follow-up history, conversations and settings are still safely stored. Activate Premium to continue using Teta2 for the next 30 days.",
    sameDashboard: "Same dashboard",
    sameData: "Same clinic data",
    unlimitedPremium: "Unlimited Premium usage",
    goSettings: "Go to Settings & activate Premium",
    reviewKicker: "PAYMENT INSTRUCTIONS SENT",
    reviewTitle: "Check your email and complete the payment.",
    reviewIntroBefore: "We sent the Premium payment instructions to",
    reviewIntroAfter:
      "Open that email and complete the payment using the payment details provided there.",
    reviewReceipt:
      "After payment, reply to the same email with your payment receipt. An administrator will verify it and activate Premium, usually within 1–6 hours.",
    reviewWait:
      "You do not need to keep this page open. The dashboard will unlock automatically after payment verification.",
    reviewContinues:
      "Your payment-review request remains active even if you leave this page or sign in again later.",
    checkStatus: "Check status now",
    checking: "Checking…",
    backWebsite: "Back to website",
    confirmKicker: "CONFIRM PREMIUM REQUEST",
    confirmTitle: "Request Premium payment instructions",
    confirmBodyA:
      "After you confirm, we will email the payment instructions to",
    confirmBodyB:
      "Complete the payment and reply to that email with your receipt. Your dashboard will unlock after administrator verification.",
    benefit1: "Payment instructions are sent immediately by email",
    benefit2: "Complete payment and reply to the email with your receipt",
    benefit3: "Premium activates after verification, usually within 1–6 hours",
    cancel: "Cancel",
    submitting: "Sending instructions…",
    continue: "Confirm & send payment instructions",
  },
  hy: {
    free: "Անվճար",
    free24: "Անվճար · 24 ժամ",
    freeEnded: "Անվճար շրջանն ավարտվել է",
    premium: "Պրեմիում",
    daysLeft: (days: number) => `Պրեմիում · մնացել է ${days} օր`,
    pendingShort: "Պրեմիում · վճարման ստուգում",
    premiumLabel: "TETA2 ՊՐԵՄԻՈՒՄ",
    unlock: "Բացեք կլինիկայի ամբողջ աշխատանքային միջավայրը 30 օրով",
    unlimited:
      "Անսահմանափակ պացիենտներ, OPG պատկերներ և ատամների հետագա հսկողություն՝ պահպանելով կլինիկայի ամբողջ պատմությունը։",
    waiting: "Սպասում է վճարման հաստատմանը",
    upgrade: "Անցնել Պրեմիումի",
    active: "Պրեմիումն ակտիվ է",
    activeHelp: "Կլինիկայի նույն աշխատանքային միջավայրն ու ամբողջ պատմությունը պահպանվում են։",
    expiredKicker: "ԱՆՎՃԱՐ ՄՈՒՏՔՆ ԱՎԱՐՏՎԵԼ Է",
    expiredTitle: "Ձեր 24-ժամյա անվճար շրջանն ավարտվել է։",
    expiredBody:
      "Պացիենտները, OPG պատկերները, հետագա հսկողության պատմությունը, զրույցներն ու կարգավորումները պահպանված են։ Ակտիվացրեք Պրեմիումը՝ Teta2-ը ևս 30 օր լիարժեք օգտագործելու համար։",
    sameDashboard: "Նույն վահանակը",
    sameData: "Նույն կլինիկայի տվյալները",
    unlimitedPremium: "Անսահմանափակ Պրեմիում օգտագործում",
    goSettings: "Գնալ Կարգավորումներ և ակտիվացնել Պրեմիումը",
    reviewKicker: "ՎՃԱՐՄԱՆ ՀՐԱՀԱՆԳՆԵՐՆ ՈՒՂԱՐԿՎԱԾ ԵՆ",
    reviewTitle: "Ստուգեք ձեր էլ․ փոստը և կատարեք վճարումը։",
    reviewIntroBefore: "Պրեմիումի վճարման հրահանգներն ուղարկել ենք",
    reviewIntroAfter:
      "Բացեք այդ նամակը և կատարեք վճարումը այնտեղ նշված վճարման տվյալներով։",
    reviewReceipt:
      "Վճարումից հետո պատասխանեք նույն նամակին և կցեք վճարման անդորրագիրը։ Ադմինիստրատորը կստուգի այն և սովորաբար 1–6 ժամվա ընթացքում կակտիվացնի Պրեմիումը։",
    reviewWait:
      "Պետք չէ այս էջը բաց պահել։ Վճարման հաստատումից հետո վահանակն ինքնաբերաբար կբացվի։",
    reviewContinues:
      "Վճարման ստուգման հայտը շարունակում է գործել, նույնիսկ եթե դուրս գաք այս էջից կամ ավելի ուշ նորից մուտք գործեք։",
    checkStatus: "Ստուգել կարգավիճակը",
    checking: "Ստուգվում է…",
    backWebsite: "Վերադառնալ կայք",
    confirmKicker: "ՀԱՍՏԱՏԵԼ ՊՐԵՄԻՈՒՄԻ ՀԱՅՏԸ",
    confirmTitle: "Ստանալ Պրեմիումի վճարման հրահանգները",
    confirmBodyA:
      "Հաստատումից հետո վճարման հրահանգները կուղարկենք",
    confirmBodyB:
      "Կատարեք վճարումը և պատասխանեք այդ նամակին՝ կցելով անդորրագիրը։ Ադմինիստրատորի ստուգումից հետո վահանակը կբացվի։",
    benefit1: "Վճարման հրահանգներն անմիջապես ուղարկվում են էլ․ փոստով",
    benefit2: "Կատարեք վճարումը և նույն նամակին ուղարկեք անդորրագիրը",
    benefit3: "Պրեմիումն ակտիվանում է ստուգումից հետո՝ սովորաբար 1–6 ժամում",
    cancel: "Չեղարկել",
    submitting: "Հրահանգներն ուղարկվում են…",
    continue: "Հաստատել և ուղարկել վճարման հրահանգները",
  },
  ru: {
    free: "Бесплатно",
    free24: "Бесплатно · 24 часа",
    freeEnded: "Бесплатный период завершен",
    premium: "Премиум",
    daysLeft: (days: number) => `Премиум · осталось ${days} дн.`,
    pendingShort: "Премиум · проверка оплаты",
    premiumLabel: "TETA2 ПРЕМИУМ",
    unlock: "Откройте полный доступ к рабочему пространству клиники на 30 дней",
    unlimited:
      "Без ограничений по пациентам, ОПТГ и наблюдению за зубами — вся история клиники сохраняется.",
    waiting: "Ожидает подтверждения оплаты",
    upgrade: "Перейти на Премиум",
    active: "Премиум активен",
    activeHelp: "Рабочее пространство и вся история клиники сохраняются без изменений.",
    expiredKicker: "БЕСПЛАТНЫЙ ДОСТУП ЗАВЕРШЕН",
    expiredTitle: "Ваш 24-часовой бесплатный период завершен.",
    expiredBody:
      "Пациенты, ОПТГ, история наблюдения, диалоги и настройки сохранены. Активируйте Премиум, чтобы продолжить полноценно пользоваться Teta2 следующие 30 дней.",
    sameDashboard: "Тот же кабинет",
    sameData: "Все данные клиники сохранены",
    unlimitedPremium: "Без ограничений в Премиум",
    goSettings: "Перейти в Настройки и активировать Премиум",
    reviewKicker: "ИНСТРУКЦИИ ПО ОПЛАТЕ ОТПРАВЛЕНЫ",
    reviewTitle: "Проверьте почту и выполните оплату.",
    reviewIntroBefore: "Инструкции по оплате Премиума отправлены на",
    reviewIntroAfter:
      "Откройте письмо и выполните оплату по указанным в нем реквизитам.",
    reviewReceipt:
      "После оплаты ответьте на это же письмо и приложите квитанцию. Администратор проверит платеж и активирует Премиум, обычно в течение 1–6 часов.",
    reviewWait:
      "Эту страницу не нужно держать открытой. После подтверждения оплаты кабинет разблокируется автоматически.",
    reviewContinues:
      "Запрос на проверку оплаты остается активным, даже если вы покинете страницу или войдете снова позже.",
    checkStatus: "Проверить статус",
    checking: "Проверяем…",
    backWebsite: "Вернуться на сайт",
    confirmKicker: "ПОДТВЕРДИТЬ ЗАПРОС ПРЕМИУМА",
    confirmTitle: "Получить инструкции по оплате Премиума",
    confirmBodyA:
      "После подтверждения инструкции по оплате будут отправлены на",
    confirmBodyB:
      "Выполните оплату и ответьте на письмо, приложив квитанцию. После проверки администратором кабинет будет разблокирован.",
    benefit1: "Инструкции по оплате сразу отправляются по электронной почте",
    benefit2: "Выполните оплату и отправьте квитанцию ответом на письмо",
    benefit3: "Премиум активируется после проверки, обычно в течение 1–6 часов",
    cancel: "Отмена",
    submitting: "Отправляем инструкции…",
    continue: "Подтвердить и отправить инструкции",
  },
} as const;

function secondsUntil(value: string | null): number | null {
  if (!value) return null;
  return Math.max(0, Math.floor((new Date(value).getTime() - Date.now()) / 1000));
}

function clock(total: number): string {
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const seconds = total % 60;
  return [hours, minutes, seconds]
    .map((value) => String(value).padStart(2, "0"))
    .join(":");
}

function isFree(user: CurrentUser | null): boolean {
  return (user?.subscription_plan || "").toUpperCase() === "FREE";
}

export function isPaymentReview(user: CurrentUser | null): boolean {
  return user?.subscription_state === "PAYMENT_REVIEW";
}

function findSettingsButton(): HTMLButtonElement | null {
  const buttons = Array.from(
    document.querySelectorAll(".care-sidebar nav button"),
  ) as HTMLButtonElement[];
  return buttons.at(-1) ?? null;
}

export function SubscriptionExperience() {
  const lang = useDashboardLanguage();
  const c = COPY[lang];
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [remaining, setRemaining] = useState<number | null>(null);
  const [settingsHost, setSettingsHost] = useState<HTMLElement | null>(null);
  const [settingsVisible, setSettingsVisible] = useState(false);
  const [confirmUpgrade, setConfirmUpgrade] = useState(false);
  const [busy, setBusy] = useState(false);
  const [checking, setChecking] = useState(false);
  const [error, setError] = useState("");
  const [previousState, setPreviousState] = useState("");

  const refresh = useCallback(async () => {
    if (!hasSession()) {
      setUser(null);
      return null;
    }
    try {
      const next = await api.me();
      setUser(next);
      setRemaining(secondsUntil(next.subscription_expires_at));
      return next;
    } catch {
      return null;
    }
  }, []);

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => void refresh(), 15000);
    return () => window.clearInterval(timer);
  }, [refresh]);

  useEffect(() => {
    if (!user?.subscription_expires_at || !isFree(user) || isPaymentReview(user)) return;
    const tick = () => setRemaining(secondsUntil(user.subscription_expires_at));
    tick();
    const timer = window.setInterval(tick, 1000);
    return () => window.clearInterval(timer);
  }, [user]);

  useEffect(() => {
    if (isPaymentReview(user)) {
      setSettingsHost(null);
      setSettingsVisible(false);
      return;
    }
    const sync = () => {
      const card = document.querySelector(
        ".account-settings .subscription-card",
      ) as HTMLElement | null;
      setSettingsVisible(Boolean(document.querySelector(".account-settings")));
      if (!card) {
        setSettingsHost(null);
        return;
      }
      let host = document.getElementById("teta2-subscription-upgrade-host");
      if (!host) {
        host = document.createElement("div");
        host.id = "teta2-subscription-upgrade-host";
        card.appendChild(host);
      }
      setSettingsHost(host);
    };
    sync();
    const observer = new MutationObserver(sync);
    observer.observe(document.body, { childList: true, subtree: true });
    return () => observer.disconnect();
  }, [user?.subscription_state]);

  const effectiveState = useMemo(() => {
    if (!user) return "";
    if (isFree(user) && remaining === 0 && user.subscription_state === "ACTIVE") {
      return "FREE_EXPIRED";
    }
    return user.subscription_state;
  }, [remaining, user]);

  const pending = effectiveState === "PAYMENT_REVIEW";

  useEffect(() => {
    if (!pending) {
      document.body.classList.remove(REVIEW_BODY_CLASS);
      return;
    }
    document.body.classList.add(REVIEW_BODY_CLASS);
    return () => document.body.classList.remove(REVIEW_BODY_CLASS);
  }, [pending]);

  useEffect(() => {
    if (!user || pending) return;
    const target = document.querySelector(
      ".care-subscription strong",
    ) as HTMLElement | null;
    if (!target) return;
    if (isFree(user)) {
      target.textContent =
        remaining === null
          ? c.free24
          : remaining > 0
            ? `${c.free} · ${clock(remaining)}`
            : c.freeEnded;
    } else if (effectiveState === "ACTIVE") {
      const days =
        remaining === null
          ? user.subscription_days_remaining
          : Math.ceil(remaining / 86400);
      target.textContent = days === null ? c.premium : c.daysLeft(days);
    }
  }, [c, effectiveState, pending, remaining, user]);

  useEffect(() => {
    if (!user) return;
    if (
      previousState === "PAYMENT_REVIEW" &&
      effectiveState === "ACTIVE" &&
      !isFree(user)
    ) {
      window.location.reload();
      return;
    }
    setPreviousState(effectiveState);
  }, [effectiveState, previousState, user]);

  const leavePendingReview = useCallback(async (destination?: string) => {
    try {
      await api.logout();
    } catch {
      // The review state is server-side and continues even if logout is unavailable.
    } finally {
      clearSession();
      if (destination) {
        window.location.assign(destination);
      } else {
        window.location.reload();
      }
    }
  }, []);

  useEffect(() => {
    if (!pending) return;
    const onPopState = () => {
      void leavePendingReview();
    };
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, [leavePendingReview, pending]);

  async function upgrade() {
    setBusy(true);
    setError("");
    try {
      await authenticatedRequest("/api/v1/platform/subscription/upgrade", {
        method: "POST",
      });
      setConfirmUpgrade(false);
      await refresh();
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  async function checkStatusNow() {
    setChecking(true);
    try {
      await refresh();
    } finally {
      setChecking(false);
    }
  }

  function goSettings() {
    findSettingsButton()?.click();
  }

  if (!user) return null;

  const expired = effectiveState === "FREE_EXPIRED" || effectiveState === "EXPIRED";
  const showExpiredBlocker = expired && !settingsVisible;

  if (pending) {
    return (
      <main className="subscription-review-page" aria-live="polite">
        <section className="subscription-review-card">
          <div className="subscription-logo-loader" aria-hidden="true">
            <span>Teta2</span>
            <LoaderCircle />
          </div>
          <small>{c.reviewKicker}</small>
          <h1>{c.reviewTitle}</h1>
          <p>
            {c.reviewIntroBefore} <strong>{user.email}</strong>. {c.reviewIntroAfter}
          </p>
          <div className="subscription-wait-line subscription-payment-instructions">
            <Mail />
            <span>{c.reviewReceipt}</span>
          </div>
          <div className="subscription-wait-line">
            <Clock3 />
            <span>{c.reviewWait}</span>
          </div>
          <p className="subscription-review-continuity">{c.reviewContinues}</p>
          <div className="subscription-review-actions">
            <button
              className="care-secondary"
              onClick={() => void leavePendingReview("/")}
            >
              <ArrowLeft />
              {c.backWebsite}
            </button>
            <button
              className="care-primary"
              disabled={checking}
              onClick={() => void checkStatusNow()}
            >
              {checking ? (
                <LoaderCircle className="subscription-spin" />
              ) : (
                <RefreshCw />
              )}
              {checking ? c.checking : c.checkStatus}
            </button>
          </div>
        </section>
      </main>
    );
  }

  return (
    <>
      {settingsHost &&
        createPortal(
          <div className="subscription-upgrade-panel">
            {isFree(user) ? (
              <>
                <div className="subscription-upgrade-copy">
                  <span>
                    <Crown />
                  </span>
                  <div>
                    <small>{c.premiumLabel}</small>
                    <strong>{c.unlock}</strong>
                    <p>{c.unlimited}</p>
                  </div>
                </div>
                <button
                  className="care-primary"
                  onClick={() => setConfirmUpgrade(true)}
                >
                  <Sparkles />
                  {c.upgrade}
                </button>
              </>
            ) : (
              <div className="subscription-premium-active">
                <Check />
                <div>
                  <strong>{c.active}</strong>
                  <span>{c.activeHelp}</span>
                </div>
              </div>
            )}
          </div>,
          settingsHost,
        )}

      {showExpiredBlocker && (
        <div className="subscription-lock-layer" role="dialog" aria-modal="true">
          <div className="subscription-lock-card">
            <span className="subscription-lock-icon">
              <LockKeyhole />
            </span>
            <small>{c.expiredKicker}</small>
            <h2>{c.expiredTitle}</h2>
            <p>{c.expiredBody}</p>
            <div className="subscription-limit-summary">
              <span>✓ {c.sameDashboard}</span>
              <span>✓ {c.sameData}</span>
              <span>✓ {c.unlimitedPremium}</span>
            </div>
            <button className="care-primary" onClick={goSettings}>
              <Crown />
              {c.goSettings}
            </button>
          </div>
        </div>
      )}

      {confirmUpgrade && (
        <div className="subscription-confirm-layer" role="dialog" aria-modal="true">
          <div className="subscription-confirm-card">
            <button
              className="subscription-close"
              aria-label={c.cancel}
              onClick={() => setConfirmUpgrade(false)}
            >
              <X />
            </button>
            <span className="subscription-lock-icon premium">
              <Crown />
            </span>
            <small>{c.confirmKicker}</small>
            <h2>{c.confirmTitle}</h2>
            <p>
              {c.confirmBodyA} <strong>{user.email}</strong>. {c.confirmBodyB}
            </p>
            <ul>
              <li>{c.benefit1}</li>
              <li>{c.benefit2}</li>
              <li>{c.benefit3}</li>
            </ul>
            {error && <div className="care-inline-error">{error}</div>}
            <div className="subscription-confirm-actions">
              <button
                className="care-secondary"
                onClick={() => setConfirmUpgrade(false)}
              >
                {c.cancel}
              </button>
              <button
                className="care-primary"
                disabled={busy}
                onClick={() => void upgrade()}
              >
                {busy ? (
                  <LoaderCircle className="subscription-spin" />
                ) : (
                  <Check />
                )}
                {busy ? c.submitting : c.continue}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

function setTextIfChanged(node: Element | null, value: string) {
  if (node && node.textContent !== value) node.textContent = value;
}

export function FreemiumPublicExperience() {
  useEffect(() => {
    const update = () => {
      if (!["/register", "/request-access"].includes(window.location.pathname)) return;
      const lang = (localStorage.getItem("teta2-product-language") || "en") as DashboardLang;
      const publicCopy = {
        en: {
          title: "Start Teta2 free for 24 hours.",
          body: "Submit your clinic details once and receive login credentials by email immediately. The one-time Free plan includes 3 patients, 1 OPG per patient and 1 tooth follow-up per OPG.",
          footer: "After you submit, check your email for the clinic login details. No payment is required for the one-time 24-hour Free plan.",
          success: "Your Free dashboard is ready",
          successBody: "Check your email now. We sent your clinic slug, username and temporary password to the email address you provided. Use those details to sign in and start your 24-hour Free access. If you do not see the email, check Spam or Junk.",
        },
        hy: {
          title: "Սկսեք Teta2-ը անվճար՝ 24 ժամով։",
          body: "Մեկ անգամ լրացրեք կլինիկայի տվյալները և մուտքի տվյալներն անմիջապես ստացեք էլ․ փոստով։ Մեկանգամյա անվճար փաթեթը ներառում է 3 պացիենտ, յուրաքանչյուր պացիենտի համար 1 OPG և յուրաքանչյուր OPG-ի համար 1 ատամի հետագա հսկողություն։",
          footer: "Հայտը ուղարկելուց հետո ստուգեք ձեր էլ․ փոստը՝ կլինիկայի մուտքի տվյալները ստանալու համար։ Մեկանգամյա 24-ժամյա անվճար փաթեթի համար վճարում չի պահանջվում։",
          success: "Ձեր անվճար վահանակը պատրաստ է",
          successBody: "Հիմա ստուգեք ձեր էլ․ փոստը։ Կլինիկայի slug-ը, օգտանունը և ժամանակավոր գաղտնաբառը ուղարկել ենք ձեր նշած հասցեին։ Այդ տվյալներով մուտք գործեք և սկսեք 24-ժամյա անվճար հասանելիությունը։ Եթե նամակը չեք տեսնում, ստուգեք Spam կամ Junk պանակները։",
        },
        ru: {
          title: "Начните пользоваться Teta2 бесплатно на 24 часа.",
          body: "Один раз заполните данные клиники и сразу получите данные для входа по электронной почте. Одноразовый бесплатный тариф включает 3 пациентов, 1 ОПТГ на пациента и наблюдение за 1 зубом на каждый ОПТГ.",
          footer: "После отправки заявки проверьте электронную почту — туда будут отправлены данные для входа. Оплата за одноразовый 24-часовой бесплатный тариф не требуется.",
          success: "Ваш бесплатный кабинет готов",
          successBody: "Проверьте электронную почту. Мы отправили на указанный адрес slug клиники, имя пользователя и временный пароль. Используйте эти данные для входа и начала 24-часового бесплатного доступа. Если письма нет во входящих, проверьте папки Спам или Нежелательная почта.",
        },
      }[lang] ?? null;
      if (!publicCopy) return;
      const story = document.querySelector(".pav2-access-story");
      setTextIfChanged(story?.querySelector("h1") ?? null, publicCopy.title);
      setTextIfChanged(story?.querySelector(":scope > p") ?? null, publicCopy.body);
      document
        .querySelectorAll(".pav2-market-preview, .pav2-live-price")
        .forEach((node) => {
          const element = node as HTMLElement;
          if (element.style.display !== "none") element.style.display = "none";
        });
      setTextIfChanged(document.querySelector(".pav2-form-footer p"), publicCopy.footer);
      const success = document.querySelector(".pav2-success");
      setTextIfChanged(success?.querySelector("h2") ?? null, publicCopy.success);
      setTextIfChanged(success?.querySelector("p") ?? null, publicCopy.successBody);
    };

    update();
    window.addEventListener("popstate", update);
    window.addEventListener("teta2-language-change", update);
    const observer = new MutationObserver(update);
    observer.observe(document.body, { childList: true, subtree: true });
    return () => {
      window.removeEventListener("popstate", update);
      window.removeEventListener("teta2-language-change", update);
      observer.disconnect();
    };
  }, []);
  return null;
}
