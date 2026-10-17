"""Decorate the freshly generated heatmap without changing contribution values."""
from pathlib import Path
import sys
import xml.etree.ElementTree as E
NS='http://www.w3.org/2000/svg'
E.register_namespace('',NS)
def tag(n): return '{'+NS+'}'+n
def add(p,n,**a): return E.SubElement(p,tag(n),{k.replace('_','-'):str(v) for k,v in a.items()})
def animate(p,attr,values,dur='6s',**kw): return add(p,'animate',attributeName=attr,values=values,dur=dur,repeatCount='indefinite',**kw)
def decorate(path):
 tree=E.parse(path); root=tree.getroot()
 if root.get('data-ayush-motion')=='1': return
 root.set('data-ayush-motion','1')
 # Keep all data geometry and text at their actual generated values.
 for parent in root.iter():
  for child in list(parent):
   if child.tag in [tag('animate'),tag('animateTransform')]: parent.remove(child)
 tops=[e for e in root.iter() if e.get('class','').startswith('cont-top-')]
 if not tops: raise ValueError('No contribution blocks found; generator format may have changed.')
 for i,e in enumerate(tops):
  e.set('stroke','#F3B552');e.set('stroke-width','1.8');e.set('stroke-opacity','0')
  animate(e,'stroke-opacity','0;0;1;0;0',keyTimes='0;0.04;0.10;0.22;1',begin=f'{-6+(i//7)*4.5/max(1,len(tops)//7):.3f}s')
 header=add(root,'g',id='motion-heading')
 add(header,'rect',x=40,y=40,width=243,height=27,fill='#F3B552',stroke='#393943',stroke_width=2)
 add(header,'text',x=52,y=59,fill='#393943',font_size=13,font_weight=700).text='GITHUB / CONTRIBUTION ACTIVITY'
 add(header,'text',x=40,y=116,fill='#393943',font_size=43,font_weight=800).text='A YEAR IN MOTION.'
 for i,h in enumerate([12,23,17,30]):
  bar=add(header,'rect',x=520+i*11,y=112-h,width=6,height=h,rx=2,fill='#387FC8')
  animate(bar,'opacity','0.35;1;0.35',dur='2s',begin=f'{-i*.25}s')
 radar=next((p for p in root.iter() if any(c.get('class')=='radar' for c in p)),None)
 if radar is not None:
  sweep=add(radar,'g',id='decorative-radar-sweep')
  add(sweep,'path',d='M0 0 L0 -144 A144 144 0 0 1 82.59 -117.96 Z',fill='#F3B552',opacity='.15')
  add(sweep,'line',x1=0,y1=0,x2=0,y2=-144,stroke='#F3B552',stroke_width=2,opacity='.85')
  add(sweep,'circle',cx=0,cy=-144,r=3,fill='#F3B552')
  add(sweep,'animateTransform',attributeName='transform',type='rotate',from_='0',to='360',dur='6s',repeatCount='indefinite').set('from','0')
  # Remove the helper's invalid from- attribute.
  for el in sweep:
   el.attrib.pop('from-',None)
 # This is a decorative orbit outside the language chart; its wedges remain fixed.
 orbit=add(root,'g',transform='translate(170 650)')
 add(orbit,'circle',cx=0,cy=0,r=126,fill='none',stroke='#E4EEF8',stroke_width=3)
 spin=add(orbit,'g')
 add(spin,'circle',cx=0,cy=0,r=126,fill='none',stroke='#F3B552',stroke_width=3,stroke_dasharray='90 702')
 add(spin,'circle',cx=126,cy=0,r=5,fill='#387FC8',stroke='#FAF9F5',stroke_width=2)
 a=add(spin,'animateTransform',attributeName='transform',type='rotate',to='360',dur='6s',repeatCount='indefinite');a.set('from','0')
 style=add(root,'style');style.text='@media (prefers-reduced-motion: reduce) { #decorative-radar-sweep { display: none; } }'
 tree.write(path,encoding='unicode')
if __name__=='__main__': decorate(Path(sys.argv[1] if len(sys.argv)>1 else 'profile-3d-contrib/profile-ayush.svg'))
