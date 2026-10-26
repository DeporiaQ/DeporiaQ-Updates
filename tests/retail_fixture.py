"""Synthetic warehouse and retail UI data; never copied into a customer database."""
from datetime import datetime,timezone

def fixture():
    names=['Olasılıksız','Aşk','Kürk Mantolu Madonna','Tutunamayanlar','Simyacı','1984','Dönüşüm','Beyaz Diş','İnce Memed','Saatleri Ayarlama Enstitüsü','Sefiller','Suç ve Ceza']
    products=[dict(id=f'00000000-0000-0000-0000-{i+1:012d}',barcode=f'978000000{i:04d}',name=name,sale_price=120+i*10,purchase_price=70+i*5,critical_stock=5,active=True) for i,name in enumerate(names)]
    lid='10000000-0000-0000-0000-000000000001';racks=[];shelves=[]
    for row in range(1,5):
        for bay in range(1,6):
            rid=f'R{row}-B{bay}';racks.append(dict(id=rid,row=row,bay=bay,levels=5,width=160,depth=50,height=230))
            for level in range(1,6):
                index=row*31+bay*7+level
                if index%5==0:continue
                shelves.append(dict(company_id='fixture',location_id=lid,rack=rid,level=level,product_id=products[index%len(products)]['id'],quantity=12+(index%5)*12,unit_width=2,verified=index%3!=0))
    inventory=[dict(product_id=p['id'],location_id=lid,quantity=1000,available=1000) for p in products]
    return dict(company_id='fixture',locations=[dict(id=lid,name='İstanbul Depo · ÖRNEK',location_type='warehouse',active=True)],products=products,inventory=inventory,
        sale_locations=[lid],channels=[],role='owner',capabilities=dict(offers=True,layout=True,finance=True,customers=True),offers=[],
        layouts=[dict(company_id='fixture',location_id=lid,version=1,spec=dict(aisle=140,racks=racks,proposed=True))],shelves=shelves,server_time=datetime.now(timezone.utc).isoformat())
