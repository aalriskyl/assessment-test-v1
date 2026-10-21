"""Export the same swimlane model to PDF and editable diagrams.net XML."""
from pathlib import Path
from math import atan2, cos, sin, pi
from xml.etree.ElementTree import Element, SubElement, ElementTree
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import A3, landscape

OUT = Path(__file__).resolve().parents[1] / "docs"
OUT.mkdir(exist_ok=True)
W, H = 1600, 1030
PW, PH = landscape(A3)
c = canvas.Canvas(str(OUT / "procurement-bpmn.pdf"), pagesize=(PW, PH))
c.setTitle("Procure - Procurement BPMN and scope")
ink, green, line = map(HexColor, ("#263F32", "#21664F", "#D4DFD4"))
mxfile = Element("mxfile", host="app.diagrams.net")
root = None
counter = 0


def new_diagram(name):
    global root
    diagram = SubElement(mxfile, "diagram", id=name, name=name)
    model = SubElement(diagram, "mxGraphModel", grid="1", page="1", pageWidth=str(W), pageHeight=str(H))
    root = SubElement(model, "root")
    SubElement(root, "mxCell", id="0")
    SubElement(root, "mxCell", id="1", parent="0")


def mx(label, x, y, w, h, style):
    global counter
    counter += 1
    cell_id = f"n{counter}"
    cell = SubElement(root, "mxCell", id=cell_id, value=label, style=style, vertex="1", parent="1")
    SubElement(cell, "mxGeometry", x=str(x), y=str(y), width=str(w), height=str(h), **{"as":"geometry"})
    return cell_id


def text(x, y, label, size=14, bold=False, color=None, center=False):
    c.setFillColor(color or ink)
    c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
    for i, value in enumerate(label.split("\n")):
        (c.drawCentredString if center else c.drawString)(x, H-y-i*(size+5), value)


def rect(x, y, w, h, fill=white, radius=0):
    c.setStrokeColor(line)
    c.setFillColor(fill)
    c.setLineWidth(1)
    c.roundRect(x,H-y-h,w,h,radius,fill=1,stroke=1)


def task(label,x,y,w=140):
    rect(x,y,w,58,HexColor("#F5F8F2"),9)
    text(x+w/2,y+25,label,13,center=True)
    return mx(label,x,y,w,58,"rounded=1;whiteSpace=wrap;html=0;fillColor=#F5F8F2;strokeColor=#9BB29D;fontSize=13;")


def event(label,x,y,end=False):
    c.setStrokeColor(green)
    c.setFillColor(white)
    c.setLineWidth(3 if end else 1.5)
    c.circle(x,H-y,17,stroke=1,fill=1)
    text(x,y+37,label,12,center=True)
    return mx(label,x-17,y-17,34,34,f"ellipse;whiteSpace=wrap;html=0;fillColor=#FFFFFF;strokeColor=#21664F;strokeWidth={3 if end else 1.5};verticalLabelPosition=bottom;verticalAlign=top;fontSize=12;")


def gateway(label,x,y):
    p=c.beginPath()
    p.moveTo(x,H-y+26)
    for xx,yy in [(x+26,y),(x,y+26),(x-26,y)]:
        p.lineTo(xx,H-yy)
    p.close()
    c.setFillColor(white)
    c.setStrokeColor(green)
    c.setLineWidth(1.5)
    c.drawPath(p,fill=1,stroke=1)
    text(x,y+5,"X",16,center=True)
    text(x,y-43,label,12,True,center=True)
    return mx("X\n"+label,x-26,y-26,52,52,"rhombus;whiteSpace=wrap;html=0;fillColor=#FFFFFF;strokeColor=#21664F;fontSize=12;")


def arrow(source,target,points,label="",at=None):
    c.setStrokeColor(green)
    c.setFillColor(green)
    c.setLineWidth(1.5)
    p=c.beginPath()
    p.moveTo(points[0][0],H-points[0][1])
    for x,y in points[1:]:
        p.lineTo(x,H-y)
    c.drawPath(p)
    x,y=points[-1]
    px,py=points[-2]
    angle=atan2(y-py,x-px)
    p=c.beginPath()
    p.moveTo(x,H-y)
    for a in (angle+pi-.4,angle+pi+.4):
        p.lineTo(x+9*cos(a),H-y-9*sin(a))
    p.close()
    c.drawPath(p,fill=1)
    if label and at:
        text(*at,label,11,color=green)
    global counter
    counter+=1
    cell=SubElement(root,"mxCell",id=f"n{counter}",value=label,edge="1",parent="1",source=source,target=target,style="edgeStyle=orthogonalEdgeStyle;rounded=0;html=0;endArrow=block;endFill=1;strokeColor=#21664F;fontSize=11;")
    geo=SubElement(cell,"mxGeometry",relative="1",**{"as":"geometry"})
    arr=SubElement(geo,"Array",**{"as":"points"})
    for x,y in points[1:-1]:
        SubElement(arr,"mxPoint",x=str(x),y=str(y))


def page(number,title,subtitle):
    c.saveState()
    c.scale(PW/W,PH/H)
    text(55,51,"PROCURE / BUSINESS ANALYSIS",13,True,green)
    text(55,95,title,32,True)
    text(55,124,subtitle,14)
    text(55,992,"Programming test v4 - Procurement | Python, PostgreSQL / SQLite | Whole IDR",11)
    text(1535,992,str(number),12,center=True)


new_diagram("Procurement process")
page(1,"Procurement process","BPMN swimlanes - one internal organization. Supplier contact and physical delivery happen outside the application.")
for i,(name,caption) in enumerate([("Requester","Business need\nand ownership"),("Approver","Need and budget"),("Purchasing","Supplier and PO"),("Receiver","Inspection and\nacceptance")]):
    y=170+i*155
    rect(55,y,1480,155,white if i%2 else HexColor("#FBFCFA"))
    rect(55,y,150,155,HexColor("#EDF3E9"))
    text(72,y+65,name,16,True,green)
    text(72,y+91,caption,11)
    mx(name,55,y,1480,155,"swimlane;horizontal=0;startSize=150;fillColor=#EDF3E9;swimlaneFillColor=#FFFFFF;strokeColor=#D4DFD4;fontSize=16;")
s=event("Need identified",245,247)
draft=task("Create draft\nwith line items",290,218)
submit=task("Submit request",480,218)
review=task("Review need\nand budget",480,373)
decision=gateway("Approved?",720,402)
revise=task("Edit full request;\nrecord revision",650,218,150)
quote=task("Compare quotes;\nselect supplier",805,528,155)
po=task("Issue PO\nwithin budget",1010,528)
inspect=task("Inspect goods\nor deliverables",1010,683)
receive=task("Record accepted\nquantities",1195,683,145)
complete=gateway("All accepted?",1410,712)
end=event("Received",1490,712,True)
arrow(s,draft,[(262,247),(290,247)])
arrow(draft,submit,[(430,247),(480,247)])
arrow(submit,review,[(550,276),(550,373)])
arrow(review,decision,[(620,402),(694,402)])
arrow(decision,revise,[(720,376),(720,276)],"No: return with reason",(735,335))
arrow(revise,submit,[(650,247),(620,247)],"Resubmit",(606,202))
arrow(decision,quote,[(746,402),(882,402),(882,528)],"Yes",(797,392))
arrow(quote,po,[(960,557),(1010,557)])
arrow(po,inspect,[(1080,586),(1080,683)],"Await delivery",(1092,638))
arrow(inspect,receive,[(1150,712),(1195,712)])
arrow(receive,complete,[(1340,712),(1384,712)])
arrow(complete,end,[(1436,712),(1473,712)],"Yes",(1442,695))
arrow(complete,inspect,[(1410,738),(1410,772),(1080,772),(1080,741)],"No: partial; await next delivery",(1165,794))
rect(55,835,1480,97,HexColor("#F1F5ED"),10)
text(78,863,"Controls at each handoff",15,True,green)
text(78,889,"Role and ownership checks | Current state validation | Atomic writes and audit | Unique delivery reference | No over-receipt",13)
text(78,914,"Before a PO exists, owners can edit or cancel. Editing approved content clears approval and starts a new revision.",12)
c.restoreState()
c.showPage()

new_diagram("Cancellation")
page(2,"Exceptions, permissions and scope","Assumptions are explicit so the diagram, WBS and application can be reviewed together.")
rect(55,170,1480,195,HexColor("#FAFCF8"),10)
text(80,205,"Cancellation subprocess - Requester lane",19,True,green)
text(80,235,"The owning requester may cancel a Draft, Submitted, Revision needed or Approved request until a PO is issued.",14)
cs=event("Request without PO",260,295)
ct=task("Confirm cancellation",480,266,210)
ce=event("Cancelled (terminal)",920,295,True)
arrow(cs,ct,[(277,295),(480,295)])
arrow(ct,ce,[(690,295),(903,295)])
text(75,410,"Business rules",20,True,green)
rules=[
    ("Approval","One stage. No self-approval. Decisions refer to the exact submitted revision; snapshots remain available."),
    ("Purchase order","One PO per request. Select a quotation for the approved revision. Copy agreed line prices; stay within budget."),
    ("Acceptance","Only inspected, accepted units count. Missing or damaged units stay outstanding until a later delivery."),
    ("Duplicates","Exact operation retries return the original result. Changed payloads and stale form versions are rejected."),
    ("Revision","Owners edit full drafts, returned or approved requests before ordering. A changed submitted revision clears approval."),
    ("Visibility","Requesters see their own requests. The other three roles see all requests, with separate action permissions."),
]
for i,(label,description) in enumerate(rules):
    y=445+i*52
    rect(55,y-22,1480,52,white if i%2 else HexColor("#F4F7F1"))
    text(75,y,label,14,True)
    text(260,y,description,13)
text(75,800,"Programming test v4 scope",19,True,green)
text(75,830,"The revised Procurement brief requires a Python web app with SQLite/PostgreSQL. Chat and mobile are not required.",14)
text(75,857,"Included: revision-aware requests, approval, supplier quotation comparison, itemized PO, partial receiving, document input and audit.",14)
text(75,884,"Excluded: warehouse stock, payments, supplier portal and real order dispatch. Optional AI requires configured provider credentials.",14)
text(75,927,"Notation: thin circle = start; thick circle = end; rounded rectangle = task; X diamond = exclusive gateway; solid arrow = sequence flow.",12)
c.restoreState()
c.showPage()

new_diagram("Quotation document input")
page(3,"Document to quotation form","Purchasing lane - extraction proposes values. Human review and the ordinary approval rules remain authoritative.")
rect(55,180,1480,430,HexColor("#FBFCFA"),10)
text(80,217,"Purchasing / current approved revision",18,True,green)
ds=event("Quotation document",140,360)
du=task("Upload and\nvalidate file",230,331,160)
de=task("Extract fields:\nPDF text or AI",480,331,160)
dg=gateway("Usable fields?",760,360)
dr=task("Review source;\nmap and correct",880,331,170)
dv=task("Confirm and save\nquotation lines",1140,331,170)
df=event("Ready to compare",1430,360,True)
arrow(ds,du,[(157,360),(230,360)])
arrow(du,de,[(390,360),(480,360)])
arrow(de,dg,[(640,360),(734,360)])
arrow(dg,dr,[(786,360),(880,360)],"Yes",(815,345))
manual=task("Enter missing fields\nmanually",675,486,170)
arrow(dg,manual,[(760,386),(760,486)],"No / timeout",(773,437))
arrow(manual,dr,[(845,515),(965,515),(965,389)])
arrow(dr,dv,[(1050,360),(1140,360)])
arrow(dv,df,[(1310,360),(1413,360)])
text(80,670,"File controls",19,True,green)
text(80,704,"PDF/JPG/PNG; maximum 5 MB; PDF maximum 5 pages; images maximum 12 megapixels. Private storage and authorized download.",14)
text(80,754,"AI boundary",19,True,green)
text(80,788,"Explicit consent for external AI processing. The extractor cannot approve requests, select suppliers or create purchase orders.",14)
text(80,822,"Missing or ambiguous values remain unknown. User verifies currency, unit prices, quantities, source evidence and supplier mapping.",14)
text(80,882,"Local labeled-PDF parsing is explicitly identified as a parser, not AI/OCR. Manual input remains available when extraction fails.",14)
c.restoreState()
c.save()
ElementTree(mxfile).write(OUT/"procurement-bpmn.drawio",encoding="utf-8",xml_declaration=True)
print("Generated BPMN PDF and editable draw.io source")
