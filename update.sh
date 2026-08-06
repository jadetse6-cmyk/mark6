#!/bin/bash
# 澳门六合彩 一键更新脚本
# 用法: bash update.sh

set -e
cd /Users/xiejinyu/macau-mark6

echo "1/4 拉取最新数据..."
python3 -c "
import csv, json, subprocess, urllib.request
DATA='macau_mark6_data.csv'
result=subprocess.run(['curl','-sL','https://history.macaumarksix.com/history/macaujc2/y/2026?t=8'],capture_output=True,text=True,timeout=15)
data=json.loads(result.stdout)
data=data if isinstance(data,list) else data.get('data',data)

# Find new draws
existing=set()
with open(DATA,'r',encoding='utf-8-sig') as f:
    for row in csv.DictReader(f):existing.add(row['期号'].strip())

new_count=0
for d in data:
    if d.get('expect','0') not in existing and int(d.get('expect','0'))>=2026218:
        code=d['openCode'];parts=[int(x) for x in code.split(',')]
        new={'期号':d['expect'],'开奖日期':d['openTime'].split(' ')[0],
             '平码1':str(parts[0]),'平码2':str(parts[1]),'平码3':str(parts[2]),
             '平码4':str(parts[3]),'平码5':str(parts[4]),'平码6':str(parts[5]),
             '特码':str(parts[6])}
        rows=[]
        with open(DATA,'r',encoding='utf-8-sig') as f2:
            for row in csv.DictReader(f2):rows.append(row)
        with open(DATA,'r',encoding='utf-8-sig') as f2:fn=list(csv.DictReader(f2).fieldnames)
        for k in fn:
            if k not in new:new[k]=''
        rows.append(new)
        rows.sort(key=lambda r:r['开奖日期'])
        with open(DATA,'w',newline='',encoding='utf-8-sig') as f2:
            w=csv.DictWriter(f2,fieldnames=fn);w.writeheader();w.writerows(rows)
        new_count+=1
        print(f'  导入 {d[\"expect\"]}: {code}')
print(f'  共导入 {new_count} 期, 总计 {len(rows)} 期')
"

echo "2/4 运行模型..."
python3 macau_model.py

echo "3/4 更新网站数据..."
python3 -c "
import csv, json
draws=[]
with open('macau_mark6_data.csv','r',encoding='utf-8-sig') as f:
    for row in csv.DictReader(f):
        draws.append({'i':row['期号'].strip(),'d':row['开奖日期'].strip(),
                      'f':[int(row[f'平码{i}']) for i in range(1,7)],'s':int(row['特码'])})
with open('index.html','r') as f:html=f.read()
old=html.find('var DRAWS = [');end=html.find('];',old)+1
html=html[:old]+'var DRAWS = '+json.dumps(draws,ensure_ascii=False)+';'+html[end+1:]
nxt=int(draws[-1]['i'])+1
import re
html=re.sub(r'v\d+',f'v{nxt}',html,count=1)
with open('index.html','w') as f:f.write(html)
print(f'  网站: {len(draws)}期 → {nxt}期')
"

echo "4/4 推送..."
git add . && git commit -m "Auto-update $(date +%Y-%m-%d)" && git push

echo "✅ 完成! 打开网站 Cmd+Shift+R"
