"""Configurable product prioritization; not a disease prediction model."""
import calendar,json
from datetime import date
from pathlib import Path
from .models import FollowupRecommendation,FollowupWindow,RiskLevel
def add_months(d,n):
 y=d.year+(d.month-1+n)//12;m=(d.month-1+n)%12+1;return date(y,m,min(d.day,calendar.monthrange(y,m)[1]))
class FollowupEngine:
 def __init__(self,path='config/dentai_followup_rules.json'):self.config=json.loads(Path(path).read_text())
 def recommend(self,tooth,analysis_date=None,override=None):
  day=analysis_date or date.today();raw=tooth.get('final_findings',tooth.get('findings',[]));find={x['type']if isinstance(x,dict)else x for x in raw};level='ROUTINE';reasons=[];rule_ids=[]
  order=self.config['priority_order']
  for rule in self.config['rules']:
   if rule['finding']in find:
    reasons.append(rule['reason']);rule_ids.append(rule.get('rule_id',rule['reason']))
    if order.index(rule['risk_level'])<order.index(level):level=rule['risk_level']
  if tooth.get('review_required'):level='URGENT_REVIEW';reasons.append('AI_REVIEW_REQUIRED');rule_ids.append('RULE_AI_REVIEW_REQUIRED')
  if len(find-{'HEALTHY'})>=2 and level not in('URGENT_REVIEW','HIGH'):level='HIGH';reasons.append('MULTIPLE_ABNORMAL_SIGNALS');rule_ids.append('RULE_MULTIPLE_ABNORMAL_SIGNALS')
  window=self.config['windows'][level];target=add_months(day,window[1]);over=False
  if override:
   level=override.get('risk_level',level);window=override.get('followup_window_months',self.config['windows'][level]);target=date.fromisoformat(override['target_date'])if override.get('target_date')else add_months(day,window[1]);reasons.append('DOCTOR_OVERRIDE');rule_ids.append('RULE_DOCTOR_OVERRIDE');over=True
  return FollowupRecommendation(risk_level=RiskLevel(level),followup_window=FollowupWindow(min_months=window[0],max_months=window[1]),recommended_followup_start=add_months(day,window[0]),recommended_followup_end=add_months(day,window[1]),target_followup_date=target,reasons=list(dict.fromkeys(reasons))or['ROUTINE_MONITORING'],source_findings=sorted(find-{'HEALTHY'}),tooth_fdi=str(tooth.get('fdi'))if tooth.get('fdi')is not None else None,rule_ids=list(dict.fromkeys(rule_ids))or['RULE_ROUTINE_MONITORING'],rule_version=self.config.get('rule_version','1.0'),doctor_overridden=over)
