"""Prepara modelo estrela, medidas DAX e relatório PBIR para Power BI Desktop."""
import csv
import gzip
import io
import json
import sqlite3
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent
MODEL = ROOT / 'Olist.SemanticModel'
REPORT = ROOT / 'Olist.Report'

def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) if isinstance(value,(dict,list)) else value, encoding='utf-8')

MEASURES = [
 ('Pedidos', 'COUNTROWS(FatoPedidos)', '#,##0', 'Volume', 'Todos os pedidos no contexto de data da compra e estado, sem excluir status.'),
 ('Pedidos entregues', 'CALCULATE([Pedidos], KEEPFILTERS(FatoPedidos[Status] = "delivered"))', '#,##0', 'Volume', 'Pedidos com status delivered, inclusive os oito sem cronologia válida para prazo.'),
 ('Vendas (R$)', 'CALCULATE(SUM(FatoPedidos[ValorProdutos]), KEEPFILTERS(FatoPedidos[Status] = "delivered"))', '"R$" #,##0.00', 'Comercial', 'Valor dos produtos de pedidos entregues. Não inclui frete e não representa lucro ou receita líquida.'),
 ('Ticket medio (R$)', 'DIVIDE([Vendas (R$)], [Pedidos entregues])', '"R$" #,##0.00', 'Comercial', 'Valor dos produtos entregues dividido pelo número de pedidos entregues.'),
 ('Pedidos cancelados', 'CALCULATE([Pedidos], KEEPFILTERS(FatoPedidos[Status] = "canceled"))', '#,##0', 'Cancelamentos', 'Somente status canceled. Unavailable não é classificado como cancelado.'),
 ('Taxa cancelamento', 'DIVIDE([Pedidos cancelados], [Pedidos])', '0.00%', 'Cancelamentos', 'Pedidos canceled divididos por todos os pedidos no contexto.'),
 ('Taxa cancelamento elegivel', 'IF([Pedidos] >= 100, [Taxa cancelamento])', '0.00%', 'Cancelamentos', 'Taxa exibida somente com pelo menos 100 pedidos no contexto, para não destacar meses de amostra mínima.'),
 ('Entregas validas', 'CALCULATE([Pedidos], KEEPFILTERS(FatoPedidos[EntregaValida] = 1))', '#,##0', 'Logistica', 'Entregues com compra, previsão e entrega válidas, entrega maior ou igual à compra.'),
 ('Entregas atrasadas', 'CALCULATE([Pedidos], KEEPFILTERS(FatoPedidos[Atrasado] = 1))', '#,##0', 'Logistica', 'Entrega válida cuja data final é posterior à data prevista, comparadas por dia.'),
 ('Taxa atraso', 'DIVIDE([Entregas atrasadas], [Entregas validas])', '0.00%', 'Logistica', 'Entregas atrasadas divididas pelas entregas válidas; cancelados não entram.'),
 ('Prazo medio (dias)', 'CALCULATE(AVERAGE(FatoPedidos[DiasEntrega]), KEEPFILTERS(FatoPedidos[EntregaValida] = 1))', '0.0" dias"', 'Logistica', 'Média de dias corridos fracionários entre a compra e a entrega, apenas entregas válidas.'),
 ('Frete medio (R$)', 'DIVIDE(CALCULATE(SUM(FatoPedidos[ValorFrete]), KEEPFILTERS(FatoPedidos[Status] = "delivered")), [Pedidos entregues])', '"R$" #,##0.00', 'Comercial', 'Frete dos pedidos entregues dividido pelos pedidos entregues.'),
 ('Vendas mes anterior (R$)', 'CALCULATE([Vendas (R$)], DATEADD(DimCalendario[Data], -1, MONTH))', '"R$" #,##0.00', 'Comercial', 'Vendas do mês anterior, usando calendário contínuo e data da compra.'),
 ('Variacao mensal vendas', 'DIVIDE([Vendas (R$)] - [Vendas mes anterior (R$)], [Vendas mes anterior (R$)])', '0.00%;-0.00%;0.00%', 'Comercial', 'Variação versus mês anterior; sem base de comparação retorna em branco. Meses incompletos exigem cautela.'),
 ('Taxa atraso elegivel', 'IF([Entregas validas] >= 100, [Taxa atraso])', '0.00%', 'Logistica', 'Taxa exibida somente com pelo menos 100 entregas válidas no contexto.'),
 ('Prazo elegivel (dias)', 'IF([Entregas validas] >= 100, [Prazo medio (dias)])', '0.0" dias"', 'Logistica', 'Prazo médio exibido somente com pelo menos 100 entregas válidas no contexto.'),
]

def prepare_data():
    con = sqlite3.connect(PROJECT/'data/olist.sqlite')
    con.row_factory = sqlite3.Row
    rows = [dict(r) for r in con.execute('''WITH i AS (
        SELECT order_id, SUM(CAST(price AS REAL)) ValorProdutos,
               SUM(CAST(freight_value AS REAL)) ValorFrete FROM items GROUP BY order_id)
        SELECT ROW_NUMBER() OVER (ORDER BY o.order_id) PedidoKey,
               date(o.order_purchase_timestamp) DataCompra, c.customer_state Estado,
               o.order_status Status, ROUND(COALESCE(i.ValorProdutos,0),2) ValorProdutos,
               ROUND(COALESCE(i.ValorFrete,0),2) ValorFrete,
               CASE WHEN f.order_id IS NOT NULL THEN 1 ELSE 0 END EntregaValida,
               f.delivery_days DiasEntrega, f.is_late Atrasado
        FROM orders o JOIN customers c ON c.customer_id=o.customer_id
        LEFT JOIN i ON i.order_id=o.order_id
        LEFT JOIN analysis_orders f ON f.order_id=o.order_id ORDER BY o.order_id''')]
    assert len(rows)==99441 and len({r['PedidoKey'] for r in rows})==99441
    assert all(r['DataCompra'] for r in rows)
    assert sum(r['EntregaValida'] for r in rows)==96470
    delivered=[r for r in rows if r['Status']=='delivered']
    assert len(delivered)==96478
    assert all(r['ValorProdutos']>0 for r in delivered), 'Pedidos entregues sem itens: revisar denominador do ticket'
    data=ROOT/'data';data.mkdir(exist_ok=True)
    text=io.StringIO(newline='');w=csv.DictWriter(text,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    (data/'pedidos.csv.gz').write_bytes(gzip.compress(text.getvalue().encode('utf-8'),mtime=0))
    (data/'pedidos.csv').write_text(text.getvalue(),encoding='utf-8',newline='')
    metrics={'pedidos':len(rows),'entregues':len(delivered),
       'vendas':round(sum(r['ValorProdutos'] for r in delivered),2),
       'ticket':sum(r['ValorProdutos'] for r in delivered)/len(delivered),
       'cancelados':sum(r['Status']=='canceled' for r in rows),
       'taxa_cancelamento':sum(r['Status']=='canceled' for r in rows)/len(rows),
       'entregas_validas':sum(r['EntregaValida'] for r in rows),
       'atrasados':sum(r['Atrasado'] or 0 for r in rows),
       'prazo_medio':sum(r['DiasEntrega'] for r in rows if r['EntregaValida'])/sum(r['EntregaValida'] for r in rows)}
    monthly=[]
    for month in sorted({r['DataCompra'][:7] for r in rows}):
        rs=[r for r in rows if r['DataCompra'].startswith(month)]
        ds=[r for r in rs if r['Status']=='delivered']; valid=[r for r in rs if r['EntregaValida']]
        monthly.append({'mes':month,'pedidos':len(rs),'entregues':len(ds),'vendas':round(sum(r['ValorProdutos'] for r in ds),2),
          'ticket':sum(r['ValorProdutos'] for r in ds)/len(ds) if ds else None,
          'cancelados':sum(r['Status']=='canceled' for r in rs),
          'taxa_cancelamento':sum(r['Status']=='canceled' for r in rs)/len(rs),
          'validas':len(valid),'atrasados':sum(r['Atrasado'] for r in valid),
          'prazo':sum(r['DiasEntrega'] for r in valid)/len(valid) if valid else None})
    states=[]
    for state in sorted({r['Estado'] for r in rows}):
        rs=[r for r in rows if r['Estado']==state];valid=[r for r in rs if r['EntregaValida']];ds=[r for r in rs if r['Status']=='delivered']
        states.append({'estado':state,'pedidos':len(rs),'vendas':round(sum(r['ValorProdutos'] for r in ds),2),
          'validas':len(valid),'atrasados':sum(r['Atrasado'] for r in valid),'taxa_atraso':sum(r['Atrasado'] for r in valid)/len(valid),
          'prazo':sum(r['DiasEntrega'] for r in valid)/len(valid)})
    write(ROOT/'validation/expected.json',{'metrics':metrics,'monthly':monthly,'states':states})
    con.close()
    return rows,metrics

def model(rows):
    fact_cols={'PedidoKey':'int64','DataCompra':'dateTime','Estado':'string','Status':'string',
      'ValorProdutos':'decimal','ValorFrete':'decimal','EntregaValida':'int64','DiasEntrega':'double','Atrasado':'int64'}
    types={'int64':'Int64.Type','decimal':'Currency.Type','double':'type number','dateTime':'type date','string':'type text'}
    type_expr=', '.join('{"'+c+'", '+types[t]+'}' for c,t in fact_cols.items())
    m='''let
    Fonte = Csv.Document(Binary.Decompress(File.Contents(PastaDados & "\\pedidos.csv.gz"), Compression.GZip), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Cabecalhos = Table.PromoteHeaders(Fonte, [PromoteAllScalars=true]),
    Nulos = Table.ReplaceValue(Cabecalhos, "", null, Replacer.ReplaceValue, Table.ColumnNames(Cabecalhos)),
    Tipos = Table.TransformColumnTypes(Nulos, {'''+type_expr+'''}, "en-US")
in
    Tipos'''
    def col(name,kind,**kw):
        return {'name':name,'dataType':kind,'sourceColumn':name,'summarizeBy':'none',**kw}
    def table(name,columns,expression):
        return {'name':name,'columns':columns,'partitions':[{'name':name,'mode':'import','source':{'type':'m','expression':expression.splitlines()}}]}
    fact=table('FatoPedidos',[col(c,t,isHidden=c not in ['Status']) for c,t in fact_cols.items()],m)
    fact['measures']=[{'name':n,'expression':e,'formatString':fmt,'displayFolder':folder,'description':desc,'lineageTag':str(uuid.uuid5(uuid.NAMESPACE_URL,n))} for n,e,fmt,folder,desc in MEASURES]
    calendar_m='''let
    Datas = List.Dates(#date(2016,1,1), 1096, #duration(1,0,0,0)),
    Tabela = Table.FromList(Datas, Splitter.SplitByNothing(), {"Data"}),
    Tipos = Table.TransformColumnTypes(Tabela, {{"Data",type date}}),
    Ano = Table.AddColumn(Tipos,"Ano",each Date.Year([Data]),Int64.Type),
    Mes = Table.AddColumn(Ano,"Mes",each Date.Month([Data]),Int64.Type),
    AnoMes = Table.AddColumn(Mes,"AnoMes",each Date.ToText([Data],"yyyy-MM"),type text),
    Ordem = Table.AddColumn(AnoMes,"AnoMesOrdem",each [Ano]*100+[Mes],Int64.Type)
in
    Ordem'''
    calendar=table('DimCalendario',[col('Data','dateTime',isKey=True,formatString='dd/MM/yyyy'),col('Ano','int64'),col('Mes','int64',isHidden=True),col('AnoMes','string',sortByColumn='AnoMesOrdem'),col('AnoMesOrdem','int64',isHidden=True)],calendar_m)
    calendar['dataCategory']='Time'
    states=sorted({r['Estado'] for r in rows})
    geography=table('DimEstado',[col('Estado','string',isKey=True)],'#table(type table [Estado=text], {'+', '.join('{"'+s+'"}' for s in states)+'})')
    bim={'name':'Olist','compatibilityLevel':1567,'model':{'culture':'pt-BR','sourceQueryCulture':'en-US','defaultPowerBIDataSourceVersion':'powerBI_V3','discourageImplicitMeasures':True,
      'dataAccessOptions':{'legacyRedirects':True,'returnErrorValuesAsNull':True},
      'expressions':[{'name':'PastaDados','kind':'m','expression':'"'+str(ROOT/'data').replace('\\','\\')+'" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]'}],
      'tables':[fact,calendar,geography],
      'relationships':[{'name':'Compra_Calendario','fromTable':'FatoPedidos','fromColumn':'DataCompra','toTable':'DimCalendario','toColumn':'Data','crossFilteringBehavior':'oneDirection','fromCardinality':'many','toCardinality':'one','isActive':True},
                       {'name':'Estado_Pedidos','fromTable':'FatoPedidos','fromColumn':'Estado','toTable':'DimEstado','toColumn':'Estado','crossFilteringBehavior':'oneDirection','fromCardinality':'many','toCardinality':'one','isActive':True}],
      'annotations':[{'name':'PBI_ProTooling','value':'["DevMode"]'},{'name':'PBI_QueryOrder','value':'["PastaDados","FatoPedidos","DimCalendario","DimEstado"]'}]}}
    write(MODEL/'model.bim',bim)
    write(MODEL/'definition.pbism',{'$schema':'https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json','version':'1.0','settings':{}})
    write(ROOT/'medidas.dax','// Referência das medidas. As medidas já estão incluídas no modelo.\n\n'+'\n\n'.join('// '+desc+'\n'+n+' =\n'+e for n,e,fmt,folder,desc in MEASURES)+'\n')
    return bim

def lit(value):
    return {'expr':{'Literal':{'Value':"'"+value+"'" if isinstance(value,str) else str(value).lower()}}}
def solid(value):return {'solid':{'color':lit(value)}}
def field(table,name,measure=False):
    return {('Measure' if measure else 'Column'):{'Expression':{'SourceRef':{'Entity':table}},'Property':name}}
def projection(table,name,measure=False):
    return {'field':field(table,name,measure),'queryRef':table+'.'+name,'nativeQueryRef':name}

def report():
    base='https://developer.microsoft.com/json-schemas/fabric/'
    write(ROOT/'Olist.pbip',{'$schema':base+'pbip/pbipProperties/1.0.0/schema.json','version':'1.0','artifacts':[{'report':{'path':'Olist.Report'}}],'settings':{'enableAutoRecovery':True}})
    write(REPORT/'definition.pbir',{'$schema':base+'item/report/definitionProperties/2.0.0/schema.json','version':'4.0','datasetReference':{'byPath':{'path':'../Olist.SemanticModel'}}})
    definition=REPORT/'definition'
    write(definition/'version.json',{'$schema':base+'item/report/definition/versionMetadata/1.0.0/schema.json','version':'2.0.0'})
    write(definition/'report.json',{'$schema':base+'item/report/definition/report/3.0.0/schema.json',
      'themeCollection':{'baseTheme':{'name':'CY24SU10','type':'SharedResources','reportVersionAtImport':{'visual':'2.0.0','report':'3.0.0','page':'2.0.0'}},'customTheme':{'name':'OlistTheme','type':'RegisteredResources','reportVersionAtImport':{'visual':'2.0.0','report':'3.0.0','page':'2.0.0'}}},
      'resourcePackages':[{'name':'RegisteredResources','type':'RegisteredResources','items':[{'name':'OlistTheme','path':'OlistTheme.json','type':'CustomTheme'}]}],
      'settings':{'useStylableVisualContainerHeader':True,'defaultFilterActionIsDataFilter':True,'defaultDrillFilterOtherVisuals':True,'allowChangeFilterTypes':True,'useEnhancedTooltips':True}})
    theme={'name':'OlistTheme','dataColors':['#205F49','#C66B3C','#86A965','#457A94','#D9B45F','#765C82'],
       'background':'#F6F5F0','foreground':'#18342E','tableAccent':'#205F49',
       'textClasses':{'title':{'fontFace':'Segoe UI Semibold','color':'#18342E','fontSize':13},'callout':{'fontFace':'Segoe UI Semibold','color':'#18342E','fontSize':26},'label':{'fontFace':'Segoe UI','color':'#61746B','fontSize':10}},
       'visualStyles':{'*':{'*':{'background':[{'show':True,'color':{'solid':{'color':'#FFFFFF'}},'transparency':0}],
           'border':[{'show':True,'color':{'solid':{'color':'#DCDDD5'}},'radius':7}],
           'visualHeader':[{'show':False}],'title':[{'show':True,'fontColor':{'solid':{'color':'#18342E'}},'fontSize':12,'fontFamily':'Segoe UI Semibold'}]}}}}
    write(REPORT/'StaticResources/RegisteredResources/OlistTheme.json',theme)
    write(definition/'pages/pages.json',{'$schema':base+'item/report/definition/pagesMetadata/1.0.0/schema.json','pageOrder':['Comercial','Logistica'],'activePageName':'Comercial'})
    z=0
    def visual(page,name,kind,x,y,w,h,title='',query=None,objects=None):
        nonlocal z
        z+=1
        if y==264:y,h=316,200
        elif y==510:y,h=527,210
        v={'$schema':base+'item/report/definition/visualContainer/2.0.0/schema.json','name':name,'position':{'x':x,'y':y,'z':z,'width':w,'height':h,'tabOrder':z},'visual':{'visualType':kind,'drillFilterOtherVisuals':True}}
        if query:v['visual']['query']={'queryState':query}
        if objects:v['visual']['objects']=objects
        v['visual']['visualContainerObjects']={'title':[{'properties':{'show':lit(bool(title)),'text':lit(title),'fontSize':lit(12)}}]}
        write(definition/'pages'/page/'visuals'/name/'visual.json',v)
        return v
    def text(page,name,text,x,y,w,h,size=13,color='#18342E',bold=False):
        obj={'general':[{'properties':{'paragraphs':[{'textRuns':[{'value':text,'textStyle':{'fontFamily':'Segoe UI','fontSize':f'{size}pt','color':color,'fontWeight':'bold' if bold else 'normal'}}]}]}}]}
        v=visual(page,name,'textbox',x,y,w,h,objects=obj)
        v['visual']['visualContainerObjects']['background']=[{'properties':{'show':lit(False)}}]
        v['visual']['visualContainerObjects']['border']=[{'properties':{'show':lit(False)}}]
        write(definition/'pages'/page/'visuals'/name/'visual.json',v)
    def card(page,name,measure,x,title):
        visual(page,name,'card',x,190,280,110,title,{'Values':{'projections':[projection('FatoPedidos',measure,True)]}},
          {'labels':[{'properties':{'fontSize':lit(20),'color':solid('#18342E'),'labelDisplayUnits':lit(1000000 if measure=='Vendas (R$)' else 1),'labelPrecision':lit(2 if '(R$)' in measure or 'Taxa' in measure else 0)}}],
           'categoryLabels':[{'properties':{'show':lit(False)}}]})
    for page,title,subtitle in [('Comercial','VENDAS & OPERAÇÃO','Quanto vendemos — e onde precisamos agir?'),('Logistica','ENTREGA & EXPERIÊNCIA','Quais estados merecem uma investigação logística?')]:
        write(definition/'pages'/page/'page.json',{'$schema':base+'item/report/definition/page/2.0.0/schema.json','name':page,'displayName':'01 · Comercial' if page=='Comercial' else '02 · Logística','displayOption':'FitToPage','width':1280,'height':800,
          'objects':{'background':[{'properties':{'color':solid('#F6F5F0'),'transparency':lit(0)}}]}})
        text(page,'title',title,30,6,850,64,23,bold=True)
        text(page,'subtitle',subtitle,32,65,800,38,12,'#61746B')
        text(page,'author','DANIEL ESTRELA  /  OLIST · 2016–2018',885,24,360,35,10,'#61746B')
        visual(page,'filter_month','slicer',32,103,580,75,'',{'Values':{'projections':[projection('DimCalendario','AnoMes')]}},{'data':[{'properties':{'mode':lit('Dropdown')}}],'selection':[{'properties':{'singleSelect':lit(False)}}]})
        visual(page,'filter_state','slicer',630,103,614,75,'',{'Values':{'projections':[projection('DimEstado','Estado')]}},{'data':[{'properties':{'mode':lit('Dropdown')}}],'selection':[{'properties':{'singleSelect':lit(False)}}]})
        text(page,'footnote','Fonte: Olist / Kaggle · Data da compra em todos os filtros · Meses de fronteira incompletos · Projeto educacional',32,764,1200,35,9,'#61746B')
    for i,(measure,title) in enumerate([('Vendas (R$)','Produtos de pedidos entregues'),('Ticket medio (R$)','Ticket médio por pedido entregue'),('Pedidos','Todos os pedidos'),('Taxa cancelamento','Cancelados / todos os pedidos')]):
        card('Comercial','kpi_'+str(i),measure,32+i*310,title)
    def chart(page,name,kind,x,y,w,h,title,cat_table,cat,measure):
        v=visual(page,name,kind,x,y,w,h,title,{'Category':{'projections':[projection(cat_table,cat)]},'Y':{'projections':[projection('FatoPedidos',measure,True)]}},
          {'categoryAxis':[{'properties':{'showAxisTitle':lit(False),'fontSize':lit(10)}}],
           'valueAxis':[{'properties':{'showAxisTitle':lit(False),'fontSize':lit(10)}}],
           'dataPoint':[{'properties':{'defaultColor':solid('#205F49')}}]})
        v['visual']['query']['sortDefinition']={'sort':[{'field':field(cat_table,cat) if cat=='AnoMes' else field('FatoPedidos',measure,True),'direction':'Ascending' if cat=='AnoMes' else 'Descending'}]}
        write(definition/'pages'/page/'visuals'/name/'visual.json',v)
        return v
    chart('Comercial','monthly_sales','lineChart',32,264,740,228,'Vendas mensais · dimensionar a operação','DimCalendario','AnoMes','Vendas (R$)')
    chart('Comercial','monthly_ticket','lineChart',790,264,452,228,'Ticket médio · investigar o mix','DimCalendario','AnoMes','Ticket medio (R$)')
    chart('Comercial','monthly_cancellations','lineChart',32,510,740,228,'Cancelamento · meses com 100+ pedidos','DimCalendario','AnoMes','Taxa cancelamento elegivel')
    chart('Comercial','state_sales','clusteredBarChart',790,510,452,228,'Vendas por estado · priorizar mercados','DimEstado','Estado','Vendas (R$)')
    for i,(measure,title) in enumerate([('Entregas validas','Entregas com datas válidas'),('Taxa atraso','Entregas após a data prevista'),('Prazo medio (dias)','Prazo médio · compra até entrega'),('Entregas atrasadas','Pedidos atrasados')]):
        card('Logistica','kpi_'+str(i),measure,32+i*310,title)
    chart('Logistica','monthly_delay','lineChart',32,264,592,228,'Taxa de atraso · meses com 100+ entregas','DimCalendario','AnoMes','Taxa atraso elegivel')
    chart('Logistica','state_delivery','clusteredBarChart',643,264,599,228,'Prazo por estado · investigar rotas (n ≥ 100)','DimEstado','Estado','Prazo elegivel (dias)')
    table_query={'Values':{'projections':[projection('DimEstado','Estado')]+[projection('FatoPedidos',m,True) for m in ['Entregas validas','Entregas atrasadas','Taxa atraso elegivel','Prazo elegivel (dias)']]}}
    visual('Logistica','state_table','tableEx',32,510,1210,228,'Estados · compare taxa de atraso e volume antes de priorizar',table_query)
    text('Logistica','note','Taxa e prazo por estado: mínimo de 100 entregas válidas. Cancelados e oito entregas com datas inválidas não entram no prazo.',34,735,1200,34,9,'#61746B')

if __name__=='__main__':
    rows,metrics=prepare_data()
    model(rows)
    report()
    print(json.dumps(metrics,ensure_ascii=False,indent=2))
    print('Projeto Power BI gerado.')
