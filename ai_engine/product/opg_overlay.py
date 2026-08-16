"""Frontend-ready independent OPG layers and tooth side panels."""
LAYERS=['TOOTH_NUMBERS','TOOTH_BOXES','CARIES','APICAL_PERIODONTITIS','IMPACTED','BONE_RESORPTION','ROOT_FRAGMENT','FURCATION_LESION','FILLINGS','CROWNS','RCT','IMPLANTS','RISK','REVIEW_REQUIRED','CHANGE_SINCE_PREVIOUS']
MAP={'FILLING':'FILLINGS','CROWN':'CROWNS','ROOT_CANAL_TREATMENT':'RCT','IMPLANT':'IMPLANTS'}
def confidence_for(f,tooth):
 vals=[]
 if tooth.get('status_v2',{}).get('prediction')==f:vals.append((tooth['status_v2'].get('confidence',0),'STATUS_V2'))
 for x in tooth.get('pathology_evidence',[]):
  if x.get('type')==f:vals.append((x.get('confidence',0),'PATHOLOGY_V41'))
 for x in tooth.get('restorations',[]):
  if x.get('detector_type')==f:vals.append((x.get('detector_confidence',0),'RESTORATION_DETECTOR_V1'))
 return max(vals,default=(tooth.get('status_v2',{}).get('confidence',0),'EVIDENCE_FUSION'))
def build_overlay(ai,followups=None,changes=None):
 followups=followups or {};changes=changes or {};layers={x:[]for x in LAYERS};teeth=[]
 for t in ai['teeth']:
  fdi=str(t['fdi']);box=t['tooth_detection']['bbox_xyxy'];find=[]
  for f in t['final_findings']:
   c,s=confidence_for(f,t);find.append({'type':f,'confidence':c,'source':s});layer=MAP.get(f,f)
   if layer in layers:layers[layer].append({'fdi':fdi,'bbox':box,'type':f,'confidence':c})
  item={'fdi':fdi,'tooth_bbox':box,'tooth_confidence':t['tooth_detection']['confidence'],'status':t['status_v2']['prediction'],'findings':find,'finding_confidences':{x['type']:x['confidence']for x in find},'pathology_boxes':[{'type':x['type'],'bbox':x['bbox_xyxy'],'confidence':x['confidence']}for x in t['pathology_evidence']],'restoration_boxes':[{'type':x['detector_type'],'bbox':x['bbox_xyxy'],'confidence':x['detector_confidence']}for x in t['restorations']],'deep_caries':t['deep_caries'],'risk_level':followups.get(fdi,{}).get('risk_level'),'followup_window':followups.get(fdi,{}).get('followup_window'),'review_required':t['review_required'],'review_reasons':t['review_reasons'],'doctor_verified':False,'previous_exam_comparison':changes.get(fdi),'raw_evidence':{'status_gate':t['status_gate'],'status_v2':t['status_v2'],'pathology':t['pathology_evidence'],'restorations':t['restorations']}}
  teeth.append(item);layers['TOOTH_NUMBERS'].append({'fdi':fdi,'bbox':box});layers['TOOTH_BOXES'].append({'fdi':fdi,'bbox':box});
  if item['risk_level']:layers['RISK'].append({'fdi':fdi,'bbox':box,'risk_level':item['risk_level']})
  if t['review_required']:layers['REVIEW_REQUIRED'].append({'fdi':fdi,'bbox':box,'reasons':t['review_reasons']})
 return {'image':ai['image'],'coordinate_space':'ORIGINAL_IMAGE_PIXELS','available_layers':LAYERS,'layers':layers,'teeth':teeth,'unmatched_pathologies':ai.get('unmatched_pathologies',[]),'unmatched_restorations':ai.get('unmatched_restorations',[])}
def side_panel(tooth):
 return {'fdi':tooth['fdi'],'current_findings':tooth['findings'],'evidence':tooth['raw_evidence'],'priority':tooth['risk_level'],'recommended_reassessment':tooth['followup_window'],'previous_exam':tooth['previous_exam_comparison'],'review_required':tooth['review_required'],'review_reasons':tooth['review_reasons'],'doctor_verification':'VERIFIED'if tooth['doctor_verified']else'UNVERIFIED','notes':[],'medical_disclaimer':'Current radiographic findings and configurable follow-up priority; not an outcome prediction.'}
