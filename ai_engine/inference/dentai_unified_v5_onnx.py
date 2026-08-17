"""CPU-only, manifest-verified implementation of DENTAI Unified V5."""
import argparse, hashlib, json, math, time
from collections import Counter,defaultdict
from io import BytesIO
from pathlib import Path
import numpy as np
import onnxruntime as ort
from PIL import Image,ImageDraw,ImageFont

FDI=[str(q*10+n) for q in range(1,5) for n in range(1,9)]; FDI_IDX={x:i for i,x in enumerate(FDI)}
QUADS={str(q):[str(q*10+n) for n in range(1,9)] for q in range(1,5)}
GATE=['HEALTHY','NON_HEALTHY']; STATUS=['HEALTHY','FILLING','CARIES','RCT_CROWN','CROWN','ROOT_CANAL_TREATMENT','RESIDUAL_ROOT']
PATH={1:'CARIES',2:'APICAL_PERIODONTITIS',3:'IMPACTED',4:'BONE_RESORPTION',5:'ROOT_FRAGMENT',6:'FURCATION_LESION'}
PTH={'CARIES':.70,'APICAL_PERIODONTITIS':.65,'IMPACTED':.65,'BONE_RESORPTION':.65,'ROOT_FRAGMENT':.30,'FURCATION_LESION':.55}
REST={1:'FILLING',2:'IMPLANT'}; EXP={'BONE_RESORPTION','FURCATION_LESION'}
MEAN=np.array([.485,.456,.406],np.float32)[:,None,None]; STD=np.array([.229,.224,.225],np.float32)[:,None,None]


class FrozenArtifactError(RuntimeError):
 """The immutable production artifact bundle is missing or has been altered."""


def expected_artifacts(manifest_path: Path) -> dict[str, str]:
 """Read the frozen manifest, retaining the manifest as the only hash authority."""
 try:
  manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
  expected={Path(item['onnx_export']['onnx_path']).name:item['onnx_export']['onnx_sha256'] for item in manifest['models'].values()}
  pre=manifest['detector_preprocessing']
  expected[Path(pre['onnx_path']).name]=pre['sha256']
 except (KeyError, TypeError, ValueError, OSError) as exc:
  raise FrozenArtifactError(f'Invalid frozen DENTAI V5 manifest: {exc}') from exc
 if len(expected)!=9:
  raise FrozenArtifactError(f'Frozen DENTAI V5 manifest must contain exactly nine artifacts, got {len(expected)}')
 return expected


def verify_artifact_bundle(model_root: Path, manifest_path: Path) -> dict[str, Path]:
 """Fail closed before session creation; only the nine frozen ONNX files are accepted."""
 expected=expected_artifacts(manifest_path)
 if not model_root.is_dir(): raise FrozenArtifactError(f'Model artifact root does not exist: {model_root}')
 actual={path.name for path in model_root.glob('*.onnx')}
 if actual != set(expected):
  raise FrozenArtifactError(f'Artifact filenames do not exactly match frozen manifest: expected={sorted(expected)}, actual={sorted(actual)}')
 paths={}
 for name,digest in expected.items():
  path=model_root/name
  actual_digest=hashlib.sha256(path.read_bytes()).hexdigest()
  if actual_digest != digest: raise FrozenArtifactError(f'SHA-256 mismatch for {name}')
  paths[name]=path
 return paths

def session(path,threads=0):
 o=ort.SessionOptions();o.graph_optimization_level=ort.GraphOptimizationLevel.ORT_ENABLE_ALL
 if threads:o.intra_op_num_threads=threads;o.inter_op_num_threads=1
 return ort.InferenceSession(str(path),sess_options=o,providers=['CPUExecutionProvider'])
def tensor(im,size,normalize=True):
 a=np.asarray(im.resize((size,size),Image.Resampling.BILINEAR),dtype=np.float32)/255.;a=a.transpose(2,0,1)
 if normalize:a=(a-MEAN)/STD
 return a[None]
def crop(im,b,pad,minimum,size):
 W,H=im.size;x1,y1,x2,y2=map(float,b);px=max(minimum,int(max(x2-x1,1)*pad));py=max(minimum,int(max(y2-y1,1)*pad))
 return tensor(im.crop((max(0,int(x1)-px),max(0,int(y1)-py),min(W,int(x2)+px),min(H,int(y2)+py))),size)
def softmax(x):x=x-x.max(axis=1,keepdims=True);e=np.exp(x);return e/e.sum(axis=1,keepdims=True)
def classify(s,x,classes):
 p=softmax(s.run(None,{'image':x.astype(np.float32)})[0])[0];i=int(p.argmax());return classes[i],float(p[i]),{c:float(v) for c,v in zip(classes,p)}
def letterbox(im,shape):
 th,tw=shape;W,H=im.size;scale=min(tw/W,th/H);nw,nh=round(W*scale),round(H*scale);px,py=(tw-nw)//2,(th-nh)//2;c=Image.new('RGB',(tw,th));c.paste(im.resize((nw,nh),Image.Resampling.BILINEAR),(px,py));a=np.asarray(c,dtype=np.float32).transpose(2,0,1)[None]/255.;return a,scale,px,py
def detect(s,pre,im,min_size,max_size):
 W,H=im.size;scale=min(min_size/min(H,W),max_size/max(H,W));nh,nw=int(H*scale),int(W*scale)
 raw=np.asarray(im,dtype=np.float32).transpose(2,0,1)[None]/255.
 x=pre.run(None,{'image':raw,'sizes':np.array([1,3,nh,nw],np.int64)})[0]
 b,sc,l=s.run(None,{'image':x});b=b.astype(float);b[:,[0,2]]*=W/nw;b[:,[1,3]]*=H/nh;b[:,[0,2]]=b[:,[0,2]].clip(0,W);b[:,[1,3]]=b[:,[1,3]].clip(0,H);return b,sc,l
def fdi_probs(s,im,b):
 W,H=im.size;x1,y1,x2,y2=map(float,b);sp=np.array([[(x1+x2)/2/W,(y1+y2)/2/H,(x2-x1)/W,(y2-y1)/H]],np.float32);return softmax(s.run(None,{'image':crop(im,b,.35,12,224),'spatial':sp})[0])[0]
CENTER_DEAD_ZONE_FRACTION=.08
def bbox_center_x(bbox):return(float(bbox[0])+float(bbox[2]))/2
def expected_viewer_side(fdi):return'LEFT'if str(fdi)[:1]in'14'else'RIGHT'
def allowed_quadrants_for_bbox(bbox,image_width):
 if image_width is None or image_width<=0:return tuple(QUADS)
 midpoint=image_width/2;half_zone=image_width*CENTER_DEAD_ZONE_FRACTION/2;center=bbox_center_x(bbox)
 if abs(center-midpoint)<=half_zone:return tuple(QUADS)
 return('1','4')if center<midpoint else('2','3')
def fdi_side_consistent(fdi,bbox,image_width):
 if not fdi or image_width is None or image_width<=0:return True
 allowed=allowed_quadrants_for_bbox(bbox,image_width)
 return len(allowed)==4 or str(fdi)[0]in allowed
def resolve(rows,image_width=None):
 groups=defaultdict(list)
 for x in rows:
  allowed=allowed_quadrants_for_bbox(x['bbox'],image_width);quadrant=max(allowed,key=lambda q:sum(float(x['probs'][FDI_IDX[c]])for c in QUADS[q]));raw_quadrant=str(x['raw'])[0]
  groups[quadrant].append({**x,'quadrant_candidates':list(allowed),'resolved_quadrant':quadrant,'side_constraint_applied':len(allowed)<4,'side_constraint_overrode_raw_quadrant':raw_quadrant not in allowed})
 out=[]
 for q in '1234':
  teeth=sorted(groups[q],key=lambda x:bbox_center_x(x['bbox']),reverse=q in '14');labels=QUADS[q];n,m=len(teeth),8;inf=1e9;dp=[[inf]*(m+1)for _ in range(n+1)];par=[[None]*(m+1)for _ in range(n+1)];dp[0][0]=0
  for i in range(n+1):
   for j in range(m+1):
    cur=dp[i][j]
    if cur>=inf:continue
    if j<m and cur+.3<dp[i][j+1]:dp[i][j+1]=cur+.3;par[i][j+1]=(i,j,'l')
    if i<n and cur+1.6<dp[i+1][j]:dp[i+1][j]=cur+1.6;par[i+1][j]=(i,j,'d')
    if i<n and j<m:
     cost=cur-math.log(max(float(teeth[i]['probs'][FDI_IDX[labels[j]]]),1e-8))-(.25 if teeth[i]['raw']==labels[j]else 0)
     if cost<dp[i+1][j+1]:dp[i+1][j+1]=cost;par[i+1][j+1]=(i,j,'a')
  j=min(range(m+1),key=lambda k:dp[n][k]+(m-k)*.3);i=n;a={}
  while i or j:
   p=par[i][j]
   if p is None:break
   pi,pj,act=p
   if act=='a':a[pi]=labels[pj]
   elif act=='d':a[pi]=None
   i,j=pi,pj
  for i,x in enumerate(teeth):out.append({**x,'resolved':a.get(i),'unresolved':a.get(i)is None})
 # Duplicate-only cleanup may use one unambiguous missing slot. Any duplicate
 # still present afterwards loses authoritative FDI while preserving its raw trace.
 for q in '1234':
  g=[x for x in out if x['resolved']and x['resolved'].startswith(q)];ordered=sorted(g,key=lambda x:bbox_center_x(x['bbox']),reverse=q in '14');cnt=Counter(x['resolved']for x in g);missing=[x for x in QUADS[q]if x not in cnt]
  if len(ordered)<=8:
   for dup,n in cnt.items():
    if n<2:continue
    members=[x for x in ordered if x['resolved']==dup];keeper=max(members,key=lambda x:x['raw_conf'])
    for x in members:
     if x is keeper:continue
     rank=ordered.index(x);previous=[int(y['resolved'][1])for y in ordered[:rank]if y is not x and y['resolved']!=dup];following=[int(y['resolved'][1])for y in ordered[rank+1:]if y is not x and y['resolved']!=dup];low=max(previous)if previous else 0;high=min(following)if following else 9;candidates=[z for z in missing if low<int(z[1])<high]
     if len(candidates)==1:x['resolved']=candidates[0];x['cleanup']=True;missing.remove(candidates[0])
  remaining=Counter(x['resolved']for x in g if x['resolved'])
  ambiguous={fdi for fdi,count in remaining.items()if count>1}
  for x in g:
   if x['resolved']in ambiguous:x['resolved']=None;x['unresolved']=True
 for x in out:
  if x['resolved']is not None and not fdi_side_consistent(x['resolved'],x['bbox'],image_width):x['resolved']=None;x['unresolved']=True
 return out
def iou(a,b):
 ix=max(0,min(a[2],b[2])-max(a[0],b[0]));iy=max(0,min(a[3],b[3])-max(a[1],b[1]));inter=ix*iy;aa=max(0,a[2]-a[0])*max(0,a[3]-a[1]);bb=max(0,b[2]-b[0])*max(0,b[3]-b[1]);return inter/(aa+bb-inter) if aa+bb>inter else 0,inter/bb if bb else 0
def attach(ds,teeth,key):
 for t in teeth:t[key]=[]
 unmatched=[]
 for d in ds:
  b=d['bbox_xyxy'];cx,cy=(b[0]+b[2])/2,(b[1]+b[3])/2;opts=[]
  for t in teeth:
   tb=t['tooth_detection']['bbox_xyxy'];u,c=iou(tb,b);tx,ty=(tb[0]+tb[2])/2,(tb[1]+tb[3])/2;dist=math.hypot(cx-tx,cy-ty)/max(math.hypot(tb[2]-tb[0],tb[3]-tb[1]),1);inside=tb[0]<=cx<=tb[2]and tb[1]<=cy<=tb[3];opts.append((c*3+u*2+inside-.25*dist,dist,t))
  best=max(opts,key=lambda x:x[0]) if opts else None
  if not best or(best[0]<=0 and best[1]>1.25):unmatched.append(d)
  else:x=dict(d);x['associated_fdi']=best[2]['fdi'];x['association_score']=round(best[0],4);best[2][key].append(x)
 return unmatched

class Engine:
 def __init__(self,model_root=Path('model_artifacts/dentai_v5'),manifest_path=Path('artifacts/production/dentai_v5_model_manifest.json'),threads=0):
  self.model_root=Path(model_root);self.manifest_path=Path(manifest_path);self.paths=verify_artifact_bundle(self.model_root,self.manifest_path)
  self.names={'pre':'detector_preprocess.onnx','tooth':'tooth_v3.onnx','fdi':'fdi_v3.onnx','gate':'status_gate_v1.onnx','status':'status_v2.onnx','path':'pathology_v41.onnx','deep':'deep_caries_v2.onnx','rd':'restoration_detector_v1.onnx','rc':'restoration_classifier_v1.onnx'}
  self.s={k:session(self.paths[v],threads)for k,v in self.names.items()};self.threads=threads
 def analyze_bytes(self,image_bytes):
  if not image_bytes: raise ValueError('protected image bytes are required')
  start=time.perf_counter();im=Image.open(BytesIO(image_bytes)).convert('RGB');b,sc,l=detect(self.s['tooth'],self.s['pre'],im,640,1600);rows=[]
  for i,(box,score,label)in enumerate(zip(b,sc,l)):
   if score<.5 or int(label)!=1:continue
   p=fdi_probs(self.s['fdi'],im,box);rows.append({'id':i,'bbox':box.tolist(),'probs':p,'raw':FDI[int(p.argmax())],'raw_conf':float(p.max()),'score':float(score)})
  rr=resolve(rows,im.width);teeth=[]
  for x in rr:
   box=x['bbox'];gp,gc,gps=classify(self.s['gate'],crop(im,box,.35,16,224),GATE);sp,ssc,sps=classify(self.s['status'],crop(im,box,.45,18,256),STATUS)
   teeth.append({'tooth_detection':{'instance_id':x['id'],'bbox_xyxy':[round(v,2)for v in box],'confidence':x['score']},'fdi':x['resolved'],'fdi_confidence':x['raw_conf'],'raw_fdi':x['raw'],'fdi_was_changed':x['raw']!=x['resolved'],'duplicate_cleanup_applied':bool(x.get('cleanup')),'fdi_review_required':x['unresolved']or x['raw_conf']<.7,'quadrant_candidates':x['quadrant_candidates'],'resolved_quadrant':x['resolved_quadrant'],'side_constraint_applied':x['side_constraint_applied'],'side_constraint_overrode_raw_quadrant':x['side_constraint_overrode_raw_quadrant'],'status_gate':{'prediction':gp,'effective_prediction':'NON_HEALTHY'if gps['NON_HEALTHY']>=.3 else'HEALTHY','confidence':gc,'probabilities':gps,'non_healthy_probability':gps['NON_HEALTHY'],'abnormal_threshold':.3},'status_v2':{'prediction':sp,'confidence':ssc,'probabilities':sps}})
  pb,ps,pl=detect(self.s['path'],self.s['pre'],im,640,1600);paths=[{'type':PATH[int(y)],'confidence':float(s),'threshold':PTH[PATH[int(y)]],'bbox_xyxy':[round(v,2)for v in x]}for x,s,y in zip(pb,ps,pl)if int(y)in PATH and s>=PTH[PATH[int(y)]]];up=attach(paths,teeth,'pathology_evidence')
  rb,rs,rl=detect(self.s['rd'],self.s['pre'],im,800,1333);rests=[]
  for box,s,y in zip(rb,rs,rl):
   if int(y)not in REST or s<.5:continue
   cp,cc,cps=classify(self.s['rc'],crop(im,box,.45,15,224),['FILLING','IMPLANT']);dt=REST[int(y)];rests.append({'type':dt,'bbox_xyxy':[round(v,2)for v in box],'detector_type':dt,'detector_confidence':float(s),'detector_threshold':.5,'classifier_type':cp,'classifier_confidence':cc,'classifier_probabilities':cps,'type_agreement':dt==cp})
  ur=attach(rests,teeth,'restorations')
  for t in teeth:
   st=t['status_v2']['prediction'];find=[]if st=='HEALTHY'else(['CROWN','ROOT_CANAL_TREATMENT']if st=='RCT_CROWN'else[st]);find +=[x['type']for x in t['pathology_evidence']]+[x['detector_type']for x in t['restorations']];find=list(dict.fromkeys(find));reasons=[]
   if st=='HEALTHY'and t['pathology_evidence']:reasons.append('STATUS_HEALTHY_CONFLICTS_WITH_PATHOLOGY')
   if st=='HEALTHY'and t['restorations']:reasons.append('STATUS_HEALTHY_CONFLICTS_WITH_RESTORATION')
   for r in t['restorations']:
    if not r['type_agreement']:reasons.append('RESTORATION_DETECTOR_CLASSIFIER_DISAGREEMENT')
    if st=='FILLING'and r['classifier_type']=='IMPLANT'and r['classifier_confidence']>=.7:reasons.append('STATUS_FILLING_CONFLICTS_WITH_IMPLANT')
   if 'CARIES'in find:
    dp,dc,dps=classify(self.s['deep'],crop(im,t['tooth_detection']['bbox_xyxy'],.55,24,256),['CARIES','DEEP_CARIES']);prob=dps['DEEP_CARIES'];t['deep_caries']={'ran':True,'prediction':dp,'confidence':dc,'probability':prob,'threshold':.65,'upgraded':prob>=.65}
    if prob>=.65:find=['DEEP_CARIES'if x=='CARIES'else x for x in find]
   else:t['deep_caries']={'ran':False,'probability':None,'threshold':.65,'upgraded':False,'reason':'NO_CARIES_EVIDENCE'}
   if any(x in EXP for x in find):reasons.append('EXPERIMENTAL_PATHOLOGY_FINDING')
   if t['fdi_review_required']:reasons.append('FDI_LOW_CONFIDENCE_OR_UNRESOLVED')
   t['final_findings']=list(dict.fromkeys(find))or['HEALTHY'];t['review_reasons']=list(dict.fromkeys(reasons));t['review_required']=bool(t['review_reasons'])
  teeth.sort(key=lambda x:(x['fdi']is None,int(x['fdi'])if x['fdi']else x['tooth_detection']['instance_id']));return {'version':'dentai-unified-v5','device':'cpu','models':{k:{'runtime':'ONNX Runtime','artifact':v}for k,v in {'tooth':'tooth_v3.onnx','fdi':'fdi_v3.onnx','status_gate':'status_gate_v1.onnx','status_v2':'status_v2.onnx','pathology':'pathology_v41.onnx','deep_caries':'deep_caries_v2.onnx','restoration_detector':'restoration_detector_v1.onnx','restoration_classifier':'restoration_classifier_v1.onnx'}.items()},'thresholds':{'tooth':.5,'status_gate_non_healthy':.3,'pathology':PTH,'deep_caries':.65,'restoration':.5},'summary':{'teeth':len(teeth),'unique_fdi':len(set(x['fdi']for x in teeth if x['fdi']is not None)),'pathology_detections':len(paths),'restorations':len(rests),'review_required':sum(x['review_required']for x in teeth),'runtime_seconds':time.perf_counter()-start},'teeth':teeth,'unmatched_pathologies':up,'unmatched_restorations':ur}
 def analyze(self,image_path):
  return self.analyze_bytes(Path(image_path).read_bytes())

def main():
 p=argparse.ArgumentParser();p.add_argument('--image',required=True);p.add_argument('--threads',type=int,default=0);p.add_argument('--model-root',type=Path,default=Path('model_artifacts/dentai_v5'));p.add_argument('--manifest',type=Path,default=Path('artifacts/production/dentai_v5_model_manifest.json'));a=p.parse_args();e=Engine(model_root=a.model_root,manifest_path=a.manifest,threads=a.threads);r=e.analyze(a.image);out=Path('artifacts/unified');out.mkdir(parents=True,exist_ok=True);jp=out/'dentai_unified_v5_onnx.json';jp.write_text(json.dumps(r,indent=2,allow_nan=False));im=Image.open(a.image).convert('RGB');d=ImageDraw.Draw(im);font=ImageFont.load_default()
 for t in r['teeth']:
  x1,y1,x2,y2=t['tooth_detection']['bbox_xyxy'];d.rectangle((x1,y1,x2,y2),outline='yellow'if t['review_required']else'lime',width=2);d.text((x1,max(0,y1-12)),f"{t['fdi']} {','.join(t['final_findings'])}"+(' !'if t['review_required']else''),fill='yellow'if t['review_required']else'white',font=font,stroke_width=1,stroke_fill='black')
 pp=out/'dentai_unified_v5_onnx_preview.jpg';im.save(pp,quality=95);print('Teeth:',len(r['teeth']),'Unique FDI:',r['summary']['unique_fdi'],'Runtime:',r['summary']['runtime_seconds']);print('JSON:',jp);print('Preview:',pp)
if __name__=='__main__':main()
