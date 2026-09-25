import { useEffect, useMemo, useState, type KeyboardEvent } from "react";
import { api, errorMessage } from "../api/client";
import type { GroqClinicalSummary, ReviewDecision, XRay } from "../api/types";
import {
  boundingBoxForFindingGroup,
  normalizeBoundingBoxToImage,
  type FindingFilter,
  type ToothFindingGroup,
  type VisionToothDetection
} from "../utils/opg";
import { groupFindingConfidence, groupFindingTone, primaryFinding } from "../utils/findingVisuals";
import { explanationForGroup } from "../utils/clinicalSummary";
import { dashboardFinding, type DashboardLang } from "../product/dashboardI18n";

const DISPLAYABLE_IMAGE_TYPES = new Set(["image/jpeg", "image/png", "image/webp"]);

interface OPGAnalysisViewerProps {
  xray: XRay | null;
  groups: ToothFindingGroup[];
  detections: VisionToothDetection[];
  clinicalSummary: GroqClinicalSummary | null;
  filter: FindingFilter;
  selectedGroupKey: string | null;
  canReview: boolean;
  decisions: Record<string, ReviewDecision | "">;
  pendingCount: number;
  decidedCount: number;
  reviewing: boolean;
  reviewError: string;
  reviewDone: string;
  canSubmitReview: boolean;
  onSubmitReview: () => void;
  onDecisionChange: (findingId: string, decision: ReviewDecision | "") => void;
  onFilterChange: (filter: FindingFilter) => void;
  onSelectedGroupChange: (key: string | null) => void;
  lang: DashboardLang;
  reviewLabel: string;
}

interface ImageSize { width: number; height: number; }

const copy = {
  en: {
    interactive: "Interactive OPG", title: "Teta2 clinical findings on the radiograph",
    legend: "Green = treated or restored teeth · red = pathological findings · red intensity reflects model confidence.",
    report: "AI report", overlay: "AI overlay", all: "All", pending: "Pending", confirmed: "Confirmed", rejected: "Rejected",
    noXray: "The X-ray for this analysis is not available.", loading: "Loading radiograph…", loadError: "The radiograph could not be loaded.",
    reportTitle: "AI clinical report", keyObservation: "Key observation", monitoring: "Monitoring", clinician: "For the clinician",
    reportDisclaimer: "AI summary does not replace clinician assessment.", close: "Close", tooth: "Tooth", finding: "finding",
    review: "Review", saving: "Saving…", saveReview: "Save review", confirm: "Confirm", reject: "Reject",
    reviewHelp: "This is an AI-assisted observation and is not a final diagnosis until reviewed by the clinician.",
    clinicalFallback: "Teta2 identified this finding in the selected tooth region. Correlate it with the clinical examination and clinician assessment.",
    selectedFinding: "Selected finding", confidence: "Confidence", reviewStatus: "Review status"
  },
  hy: {
    interactive: "Ինտերակտիվ OPG", title: "Teta2-ի կլինիկական հայտնաբերումները ռենտգեն պատկերի վրա",
    legend: "Կանաչ՝ բուժված կամ վերականգնված ատամներ · կարմիր՝ հնարավոր պաթոլոգիական փոփոխություններ · կարմիրի ուժգնությունը ցույց է տալիս մոդելի վստահության աստիճանը։",
    report: "ԱԲ զեկույց", overlay: "ԱԲ շերտ", all: "Բոլորը", pending: "Սպասող", confirmed: "Հաստատված", rejected: "Մերժված",
    noXray: "Այս վերլուծության ռենտգեն պատկերը հասանելի չէ։", loading: "Բեռնվում է ռենտգեն պատկերը…", loadError: "Չհաջողվեց բեռնել ռենտգեն պատկերը։",
    reportTitle: "ԱԲ կլինիկական զեկույց", keyObservation: "Հիմնական դիտարկում", monitoring: "Հետագա հսկողություն", clinician: "Բժշկի ուշադրությանը",
    reportDisclaimer: "ԱԲ ամփոփումը չի փոխարինում բժշկի կլինիկական գնահատմանը։", close: "Փակել", tooth: "Ատամ", finding: "հայտնաբերում",
    review: "Վերանայում", saving: "Պահպանվում է…", saveReview: "Պահպանել վերանայումը", confirm: "Հաստատել", reject: "Մերժել",
    reviewHelp: "Սա ԱԲ-ի օժանդակ դիտարկում է և մինչև բժշկի վերանայումը վերջնական ախտորոշում չէ։",
    clinicalFallback: "Teta2-ը նշել է այս փոփոխությունը ընտրված ատամի շրջանում։ Այն պետք է համադրել կլինիկական զննման և բժշկի գնահատման հետ։",
    selectedFinding: "Ընտրված հայտնաբերում", confidence: "Վստահության աստիճան", reviewStatus: "Վերանայման կարգավիճակ"
  },
  ru: {
    interactive: "Интерактивный ОПТГ", title: "Клинические результаты Teta2 на рентгеновском снимке",
    legend: "Зеленым отмечены пролеченные или восстановленные зубы · красным — возможные патологические изменения · интенсивность красного отражает уверенность модели.",
    report: "Отчет ИИ", overlay: "Слой ИИ", all: "Все", pending: "Ожидает проверки", confirmed: "Подтверждено", rejected: "Отклонено",
    noXray: "Рентгеновский снимок для этого анализа недоступен.", loading: "Загрузка рентгеновского снимка…", loadError: "Не удалось загрузить рентгеновский снимок.",
    reportTitle: "Клинический отчет ИИ", keyObservation: "Ключевое наблюдение", monitoring: "Наблюдение", clinician: "Для врача",
    reportDisclaimer: "Резюме ИИ не заменяет клиническую оценку врача.", close: "Закрыть", tooth: "Зуб", finding: "результат",
    review: "Проверка", saving: "Сохранение…", saveReview: "Сохранить проверку", confirm: "Подтвердить", reject: "Отклонить",
    reviewHelp: "Это вспомогательное наблюдение ИИ, а не окончательный диагноз до проверки врачом.",
    clinicalFallback: "Teta2 отметил это изменение в области выбранного зуба. Сопоставьте его с клиническим осмотром и оценкой врача.",
    selectedFinding: "Выбранный результат", confidence: "Уверенность", reviewStatus: "Статус проверки"
  }
} as const;

export function OPGAnalysisViewer({
  xray, groups, detections, clinicalSummary, filter, selectedGroupKey, canReview, decisions,
  pendingCount, decidedCount, reviewing, reviewError, reviewDone, canSubmitReview, onSubmitReview,
  onDecisionChange, onFilterChange, onSelectedGroupChange, lang
}: OPGAnalysisViewerProps) {
  const text = copy[lang];
  const [imageUrl,setImageUrl]=useState(""); const [imageSize,setImageSize]=useState<ImageSize|null>(null); const [imageError,setImageError]=useState("");
  const [overlaysVisible,setOverlaysVisible]=useState(true); const [hovered,setHovered]=useState<string|null>(null); const [reportOpen,setReportOpen]=useState(false);
  const filters: Array<{value:FindingFilter;label:string}> = [
    {value:"ALL",label:text.all},{value:"PENDING",label:text.pending},{value:"CONFIRMED",label:text.confirmed},{value:"REJECTED",label:text.rejected}
  ];
  const selectedGroup=useMemo(()=>groups.find((group)=>group.key===selectedGroupKey)??null,[groups,selectedGroupKey]);
  const selectedExplanation=useMemo(()=>explanationForGroup(clinicalSummary,selectedGroup),[clinicalSummary,selectedGroup]);
  const displayable=xray?DISPLAYABLE_IMAGE_TYPES.has(xray.mime_type):false;
  const projected=useMemo(()=>{
    if(!imageSize)return [];
    return groups.flatMap((group)=>{
      const raw=boundingBoxForFindingGroup(group,detections,imageSize.width,imageSize.height); if(!raw)return [];
      const box=normalizeBoundingBoxToImage(raw,imageSize.width,imageSize.height); if(!box)return [];
      return [{group,box,tone:groupFindingTone(group),confidence:groupFindingConfidence(group),primary:primaryFinding(group)}];
    });
  },[groups,detections,imageSize]);
  const selectedRegion=useMemo(()=>projected.find((region)=>region.group.key===selectedGroupKey)??null,[projected,selectedGroupKey]);
  const focusPosition=useMemo(()=>{
    if(!selectedRegion||!imageSize)return "50% 50%";
    const [x1,y1,x2,y2]=selectedRegion.box;
    const x=(((x1+x2)/2)/imageSize.width)*100;
    const y=(((y1+y2)/2)/imageSize.height)*100;
    return `${x}% ${y}%`;
  },[selectedRegion,imageSize]);
  const activeKey=hovered??selectedGroupKey;

  useEffect(()=>{
    let active=true; setImageUrl(""); setImageSize(null); setImageError(""); setReportOpen(false);
    if(!xray||!DISPLAYABLE_IMAGE_TYPES.has(xray.mime_type))return()=>{active=false};
    api.xrayDownload(xray.id).then((download)=>{if(active)setImageUrl(download.url)}).catch((reason)=>{if(active)setImageError(errorMessage(reason))});
    return()=>{active=false};
  },[xray?.id,xray?.mime_type]);

  useEffect(()=>{
    if(!selectedGroup)return;
    const close=(event:globalThis.KeyboardEvent)=>{if(event.key==="Escape")onSelectedGroupChange(null)};
    window.addEventListener("keydown",close); return()=>window.removeEventListener("keydown",close);
  },[selectedGroup,onSelectedGroupChange]);

  function keyboard(event:KeyboardEvent<SVGGElement>,key:string){if(event.key==="Enter"||event.key===" "){event.preventDefault();onSelectedGroupChange(key)}}
  function colors(tone:"RESTORATIVE"|"PATHOLOGY",confidence:number){
    if(tone==="RESTORATIVE")return {fill:"rgba(34,197,94,.105)",stroke:"rgba(74,222,128,.94)",glow:"rgba(34,197,94,.46)"};
    const strength=Math.max(.2,Math.min(1,confidence)); return {fill:`rgba(239,68,68,${.045+strength*.17})`,stroke:`rgba(248,80,80,${.58+strength*.4})`,glow:`rgba(239,68,68,${.12+strength*.46})`};
  }
  const localizedType=(value:string)=>dashboardFinding(value,lang);
  const localizedReviewStatus=(value:string)=>value==="CONFIRMED"?text.confirmed:value==="REJECTED"?text.rejected:text.pending;
  const modalHeadline=selectedGroup?localizedType(primaryFinding(selectedGroup)?.finding_type??""):"";
  const modalTypes=selectedGroup?selectedGroup.findings.map((finding)=>localizedType(finding.finding_type)):[];
  const clinicalExplanation=selectedExplanation?.clinical_explanation || (selectedGroup?`${text.clinicalFallback} ${modalTypes.join(", ")}.`:"");
  const reviewExplanation=selectedExplanation?.review_explanation || text.reviewHelp;

  return <section className="opg-workspace medical-opg card findings-only-opg">
    <div className="medical-opg-header"><div><p className="eyebrow">{text.interactive}</p><h3>{text.title}</h3><p>{text.legend}</p></div><div className="medical-viewer-actions">{clinicalSummary&&<button className={`opg-report-button${reportOpen?" active":""}`} type="button" onClick={()=>setReportOpen((value)=>!value)}>✦ {text.report}</button>}<label className="medical-switch"><input type="checkbox" checked={overlaysVisible} onChange={(event)=>setOverlaysVisible(event.target.checked)}/><span aria-hidden="true"/>{text.overlay}</label><div className="finding-filter-pills" aria-label={text.review}>{filters.map((option)=><button className={filter===option.value?"active":""} key={option.value} type="button" onClick={()=>onFilterChange(option.value)}>{option.label}</button>)}</div></div></div>
    <div className="opg-cinematic-shell">
      {!xray&&<div className="opg-placeholder">{text.noXray}</div>}
      {xray&&!displayable&&<div className="opg-placeholder dicom-state"><strong>DICOM</strong><span>{xray.original_filename}</span></div>}
      {xray&&displayable&&!imageUrl&&!imageError&&<div className="opg-placeholder">{text.loading}</div>}
      {imageError&&<div className="opg-placeholder error-panel">{imageError}</div>}
      {imageUrl&&<div className="opg-image-stage cinematic-stage finding-stage"><img src={imageUrl} alt={`${text.interactive} · ${xray?.original_filename??""}`} onLoad={(event)=>{setImageSize({width:event.currentTarget.naturalWidth,height:event.currentTarget.naturalHeight});setImageError("")}} onError={()=>setImageError(text.loadError)}/><div className="stage-vignette" aria-hidden="true"/>
        {overlaysVisible&&imageSize&&<svg className="opg-overlay medical-overlay finding-only-overlay" viewBox={`0 0 ${imageSize.width} ${imageSize.height}`} preserveAspectRatio="xMidYMid meet" aria-label={text.title}>{projected.map((region)=>{const [x1,y1,x2,y2]=region.box;const width=x2-x1;const height=y2-y1;const active=activeKey===region.group.key;const palette=colors(region.tone,region.confidence);const tooth=region.group.toothCode??"?";return <g className={`clinical-finding-region ${region.tone==="RESTORATIVE"?"restorative":"pathology"}${active?" active":""}`} key={region.group.key} role="button" tabIndex={0} aria-label={`${text.tooth} ${tooth}: ${region.primary?localizedType(region.primary.finding_type):text.finding}`} onClick={()=>onSelectedGroupChange(region.group.key)} onKeyDown={(event)=>keyboard(event,region.group.key)} onMouseEnter={()=>setHovered(region.group.key)} onMouseLeave={()=>setHovered(null)}><rect x={x1} y={y1} width={width} height={height} rx={Math.max(5,width*.08)} fill={palette.fill} stroke={palette.stroke} strokeWidth={active?2.6:1.7} vectorEffect="non-scaling-stroke" style={{filter:`drop-shadow(0 0 ${active?11:5}px ${palette.glow})`}}/><text x={(x1+x2)/2} y={(y1+y2)/2} textAnchor="middle" fontSize={Math.max(15,Math.min(width*.25,imageSize.width/55))} fill="rgba(255,255,255,.72)" fontWeight="800">{Math.round(region.confidence*100)}%</text><g pointerEvents="none"><rect x={x1} y={Math.max(2,y1-24)} width="38" height="20" rx="10" fill="rgba(8,13,25,.92)" stroke={palette.stroke}/><text x={x1+19} y={Math.max(16,y1-10)} textAnchor="middle" fontSize="12" fill="#fff" fontWeight="800">{tooth}</text></g></g>})}</svg>}
        {clinicalSummary&&reportOpen&&<aside className="opg-report-panel"><button type="button" onClick={()=>setReportOpen(false)} aria-label={text.close}>×</button><span className="eyebrow">{text.reportTitle}</span><h4>{clinicalSummary.doctor_summary}</h4>{clinicalSummary.important_changes[0]&&<p><strong>{text.keyObservation}</strong>{clinicalSummary.important_changes[0]}</p>}{clinicalSummary.monitoring_points[0]&&<p><strong>{text.monitoring}</strong>{clinicalSummary.monitoring_points[0]}</p>}{clinicalSummary.questions_for_doctor[0]&&<p><strong>{text.clinician}</strong>{clinicalSummary.questions_for_doctor[0]}</p>}<small>{text.reportDisclaimer}</small></aside>}
        {canReview&&pendingCount>0&&<div className="opg-review-dock"><span>{text.review} {decidedCount}/{pendingCount}</span>{reviewError&&<em>{reviewError}</em>}{reviewDone&&<em className="success">{reviewDone}</em>}<button type="button" disabled={!canSubmitReview||reviewing} onClick={onSubmitReview}>{reviewing?text.saving:text.saveReview}</button></div>}
      </div>}
    </div>
    {selectedGroup&&<div className="finding-dialog-backdrop" role="presentation" onMouseDown={(event)=>{if(event.target===event.currentTarget)onSelectedGroupChange(null)}}>
      <section className="finding-dialog" role="dialog" aria-modal="true" aria-label={`${text.tooth} ${selectedGroup.toothCode??"?"}: ${modalHeadline}`} lang={lang}>
        <button className="finding-dialog-close" type="button" onClick={()=>onSelectedGroupChange(null)} aria-label={text.close}>×</button>
        <div className={`finding-dialog-visual ${groupFindingTone(selectedGroup)==="RESTORATIVE"?"restorative":"pathology"}`}>
          {imageUrl&&<img src={imageUrl} alt={`${text.tooth} ${selectedGroup.toothCode??"?"}`} style={{objectPosition:focusPosition}}/>}
          <div className="finding-visual-shade"/>
          <div className="finding-visual-target" aria-hidden="true"><i/><i/><span>{selectedGroup.toothCode??"?"}</span></div>
          <div className="finding-visual-label"><span>✦</span><strong>Teta2 · {text.selectedFinding}</strong></div>
        </div>
        <div className="finding-dialog-content">
          <header className="finding-dialog-heading">
            <div><p className="eyebrow">{text.selectedFinding} · FDI {selectedGroup.toothCode??"?"}</p><h2>{modalHeadline}</h2></div>
            <span className="finding-count-badge">{Math.round(groupFindingConfidence(selectedGroup)*100)}%</span>
          </header>
          <div className="finding-chip-row premium-finding-chips">
            {selectedGroup.findings.map((finding)=><span key={finding.id}>{localizedType(finding.finding_type)}</span>)}
          </div>
          <div className="clinical-story-grid">
            <article className="clinical-story-card primary-story"><span className="story-icon">◉</span><div><small>{text.selectedFinding}</small><p>{clinicalExplanation}</p></div></article>
            <article className="clinical-story-card"><span className="story-icon">✓</span><div><small>{text.clinician}</small><p>{reviewExplanation}</p></div></article>
          </div>
          <div className="finding-confidence-list">
            {selectedGroup.findings.map((finding)=><div key={finding.id}><span>{localizedType(finding.finding_type)}</span><strong>{typeof finding.confidence==="number"?`${Math.round(finding.confidence*100)}%`:"—"}</strong><small>{localizedReviewStatus(finding.review_status)}</small></div>)}
          </div>
          {canReview&&selectedGroup.findings.some((finding)=>finding.review_status==="PENDING")&&<section className="micro-review-card">
            <div><strong>{text.review}</strong><small>{text.reviewHelp}</small></div>
            <div className="micro-review-items">
              {selectedGroup.findings.filter((finding)=>finding.review_status==="PENDING").map((finding)=><div key={finding.id} className="micro-review-item">
                <span>{localizedType(finding.finding_type)}</span>
                <div className="decision-segmented" role="group" aria-label={text.review}>
                  <button className={decisions[finding.id]==="CONFIRMED"?"selected confirm":""} type="button" onClick={()=>onDecisionChange(finding.id,"CONFIRMED")}>{text.confirm}</button>
                  <button className={decisions[finding.id]==="REJECTED"?"selected reject":""} type="button" onClick={()=>onDecisionChange(finding.id,"REJECTED")}>{text.reject}</button>
                </div>
              </div>)}
            </div>
          </section>}
        </div>
      </section>
    </div>}
  </section>;
}
