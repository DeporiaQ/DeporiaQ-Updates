"""Pure presentation calculations; authoritative prices and stock stay on server."""
from decimal import Decimal, ROUND_HALF_UP
import unicodedata

def folded(text):
    text=str(text).replace('İ','I').replace('ı','i')
    return ''.join(c for c in unicodedata.normalize('NFKD',text.casefold()) if not unicodedata.combining(c))

def find_products(products,text):
    text=text.strip();needle=folded(text)
    active=[p for p in products if p.get('active')]
    exact=[p for p in active if str(p.get('barcode','')).strip()==text]
    if exact:return exact
    return [p for p in active if needle and (needle in folded(p['name']) or needle in folded(p['barcode']))]

def money(value):
    return f'{Decimal(str(value or 0)):,.2f}'.replace(',','_').replace('.',',').replace('_','.')+' ₺'

def offer_totals(products,items,discount):
    lookup={p['id']:p for p in products};normal=Decimal(0);total=Decimal(0);cost=Decimal(0)
    for item in items:
        product=lookup[item['product_id']];qty=Decimal(str(item['quantity']))
        price=Decimal(str(product['sale_price']));normal+=qty*price
        total+=qty*(price*(1-Decimal(str(discount))/100)).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
        cost+=qty*Decimal(str(product['purchase_price']))
    return normal,total,cost

def warehouse_scene(layout,shelves,products,selected='',empty_only=False):
    """Centimetre geometry, estimated linear occupancy, addressable pickable bins."""
    spec=layout.get('spec',{});racks=spec.get('racks',[]);aisle=float(spec.get('aisle',140))
    by_slot={};names={p['id']:p['name'] for p in products}
    for s in shelves:
        if s['location_id']==layout.get('location_id'):by_slot.setdefault((s['rack'],s['level']),[]).append(s)
    max_depth=max([float(r['depth']) for r in racks]+[50]);parts=[];labels=[];positions={};used=0;capacity=0;verified=0;placed=0
    row_offsets={};max_x=max_z=0
    def box(x,y,z,w,h,d,color,rack='',level=0,product='',metal=0):
        parts.append(dict(x=x,y=y,z=z,w=w,h=h,d=d,color=color,rack=rack,level=level,product=product,metal=metal))
    colors=['#6aa5c3','#bd9470','#879b72','#ad7888','#7b83ad','#b49d64']
    for rack in sorted(racks,key=lambda r:(r['row'],r['bay'])):
        w,d,h=float(rack['width']),float(rack['depth']),float(rack['height']);n=int(rack['levels']);rid=rack['id']
        x=row_offsets.get(rack['row'],0)+w/2;z=(rack['row']-1)*(max_depth+aisle)+d/2;row_offsets[rack['row']]=x+w/2+float(spec.get('bay_gap',16))
        max_x=max(max_x,x+w/2);max_z=max(max_z,z+d/2);capacity+=w*n
        labels.append(dict(text=rid,x=x,y=h+24,z=z));positions[rid]=(x,z)
        for side_x in (-1,1):
            for side_z in (-1,1):
                box(x+side_x*(w/2-2),h/2,z+side_z*(d/2-2),4,h,4,'#48647d',metal=.75)
                box(x+side_x*(w/2-2),2,z+side_z*(d/2-2),12,4,12,'#526478',metal=.6)
        for level in range(1,n+1):
            y=12+(level-1)*(h-24)/n;entries=by_slot.get((rid,level),[])
            occupied=sum(s['quantity']*float(s['unit_width']) for s in entries);used+=occupied
            box(x,y,z,w,2.5,d,'#8a9aab',rid,level,metal=.6)
            for side in (-1,1):box(x,y-3,z+side*d/2,w,6,4,'#d39145',rid,level,metal=.4)
            # Empty space is a selectable translucent-looking green shelf strip.
            if occupied<w:box(x-w/2+occupied+(w-occupied)/2,y+2,z,w-occupied,1.5,d-6,'#547f76',rid,level)
            offset=0
            for entry in entries:
                width=entry['quantity']*float(entry['unit_width']);placed+=entry['quantity'];verified+=entry['quantity'] if entry.get('verified') else 0
                if not empty_only or selected==entry['product_id']:
                    segments=min(3 if len(racks)>40 else 12,max(1,entry['quantity']));step=width/segments
                    for seg in range(segments):
                        color='#35d8d1' if entry['product_id']==selected else colors[sum(map(ord,entry['product_id']))%len(colors)]
                        book_h=min(32,(h-24)/n-10)+(seg%3)*1.2
                        box(x-w/2+offset+(seg+.5)*step,y+2+book_h/2,z,max(.2,step-.6),book_h,d*.62,color,rid,level,entry['product_id'])
                offset+=width
    return dict(parts=parts,labels=labels,positions=positions,width=max_x+100,depth=max_z+100,
                centerX=max_x/2,centerZ=max_z/2,used=used,capacity=capacity,placed=placed,verified=verified,
                occupancy=100*used/capacity if capacity else 0)

def free_shelves(layout,shelves,quantity,unit_width):
    result=[];usage={}
    for s in shelves:
        if s['location_id']==layout['location_id']:
            key=(s['rack'],s['level']);usage[key]=usage.get(key,0)+s['quantity']*float(s['unit_width'])
    for rack in layout['spec']['racks']:
        for level in range(1,int(rack['levels'])+1):
            free=float(rack['width'])-usage.get((rack['id'],level),0)
            if free+1e-6>=quantity*unit_width:result.append((rack['id'],level,free))
    return sorted(result,key=lambda x:(x[2],x[0],x[1]))
