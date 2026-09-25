"""Build tableau/Medicare Cost Drivers.twbx from output/tableau_data.csv.

A .twbx is a zip holding a .twb (workbook XML) and the data it uses. This script writes the XML by hand,
so treat the workbook as a starting point: open it in Tableau Desktop, check the data source connects,
then polish the formatting. What's in it:
  * data source on the packaged CSV, with captions, types and the PMPM calculations
  * 4 worksheets: PMPM by category (stacked bars), total PMPM trend, subcategory PMPM, primary care share
  * 1 dashboard laying out the four sheets, with Medicaid / age / sex filter cards
Demographic filters are context filters on every sheet, because the member-month denominator is a FIXED
LOD and FIXED ignores ordinary filters. In Tableau, set each filter card to "Apply to all worksheets
using this data source".
"""
import pathlib, zipfile
from xml.sax.saxutils import quoteattr, escape

ROOT = pathlib.Path(__file__).resolve().parents[1]
CSV = ROOT / "output" / "tableau_data.csv"
OUT = ROOT / "tableau" / "Medicare Cost Drivers.twbx"
DS = "federated.0mcd0pmpm00001"          # data source internal name
CONN = "textscan.0mcd0csv000001"         # named connection
Q = lambda s: quoteattr(s)                # XML attribute quoting

CATS = ["Inpatient Hospital", "Outpatient Hospital", "Professional", "Long-Term Care", "Retail Pharmacy", "Other"]
COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]

# (name, datatype, role, type, caption)
FIELDS = [
    ("row_type", "string", "dimension", "nominal", "Row Type"),
    ("yr", "integer", "dimension", "ordinal", "Year"),
    ("service_category", "string", "dimension", "nominal", "Service Category"),
    ("subcategory", "string", "dimension", "nominal", "Subcategory"),
    ("type_of_service", "string", "dimension", "nominal", "Type of Service"),
    ("service_group", "string", "dimension", "nominal", "Primary Care Service Group"),
    ("dual_status", "string", "dimension", "nominal", "Medicaid (Dual) Status"),
    ("age_band", "string", "dimension", "nominal", "Age Band"),
    ("sex", "string", "dimension", "nominal", "Sex"),
    ("allowed", "real", "measure", "quantitative", "Allowed $"),
    ("pc_allowed", "real", "measure", "quantitative", "Primary Care Allowed $"),
    ("ab_mm", "integer", "measure", "quantitative", "A+B FFS Member Months (row)"),
    ("pd_mm", "integer", "measure", "quantitative", "Part D Member Months (row)"),
]

# (internal name, caption, datatype, role, type, formula, default number format)
CALCS = [
    ("Calculation_mm_ab", "Member Months A+B FFS", "integer", "measure", "quantitative",
     "{FIXED [yr] : SUM([ab_mm])}", None),
    ("Calculation_mm_pd", "Member Months Part D", "integer", "measure", "quantitative",
     "{FIXED [yr] : SUM([pd_mm])}", None),
    ("Calculation_denom", "PMPM Denominator", "integer", "measure", "quantitative",
     "IF [service_category] = 'Retail Pharmacy' THEN [Calculation_mm_pd] ELSE [Calculation_mm_ab] END", None),
    ("Calculation_pmpm", "PMPM", "real", "measure", "quantitative",
     "// Allowed $ per member per month. Retail pharmacy uses Part D months, everything else A+B FFS months.\n"
     "SUM([allowed]) / MIN([Calculation_denom])", '"$"#,##0.00'),
    ("Calculation_total_pmpm", "Total PMPM", "real", "measure", "quantitative",
     "SUM(IF [service_category] <> 'Retail Pharmacy' THEN [allowed] END) / MIN([Calculation_mm_ab])\n"
     "+ ZN(SUM(IF [service_category] = 'Retail Pharmacy' THEN [allowed] END) / MIN([Calculation_mm_pd]))",
     '"$"#,##0.00'),
    ("Calculation_pc_share", "Primary Care % of Medical Spend", "real", "measure", "quantitative",
     "SUM([pc_allowed]) / SUM(IF [row_type] = 'spend' AND [service_category] <> 'Retail Pharmacy' THEN [allowed] END)",
     "0.00%"),
    ("Calculation_pc_pmpm", "Primary Care PMPM", "real", "measure", "quantitative",
     "SUM([pc_allowed]) / MIN([Calculation_mm_ab])", '"$"#,##0.00'),
]

def inst(field, kind):
    """Column-instance reference, e.g. [none:yr:ok] or [usr:Calculation_pmpm:qk]."""
    return {"dim": f"[none:{field}:nk]", "ord": f"[none:{field}:ok]", "calc": f"[usr:{field}:qk]"}[kind]

def ref(field, kind):
    return f"[{DS}].{inst(field, kind)}"

def column_xml(name):
    for n, dt, role, typ, cap in FIELDS:
        if n == name:
            return f"<column caption={Q(cap)} datatype='{dt}' name='[{n}]' role='{role}' type='{typ}' />"
    for n, cap, dt, role, typ, formula, fmt in CALCS:
        if n == name:
            f = f" default-format={Q(fmt)}" if fmt else ""
            return (f"<column caption={Q(cap)} datatype='{dt}'{f} name='[{n}]' role='{role}' type='{typ}'>"
                    f"<calculation class='tableau' formula={Q(formula)} /></column>")
    raise KeyError(name)

def instance_xml(field, kind):
    deriv, typ = ("User", "quantitative") if kind == "calc" else ("None", "ordinal" if kind == "ord" else "nominal")
    return f"<column-instance column='[{field}]' derivation='{deriv}' name='{inst(field, kind)}' pivot='key' type='{typ}' />"

def datasource_xml():
    rel_cols = "".join(
        f"<column datatype='{dt}' name={Q(n)} ordinal='{i}' />" for i, (n, dt, *_ ) in enumerate(FIELDS))
    cols = "".join(column_xml(n) for n, *_ in FIELDS) + "".join(column_xml(c[0]) for c in CALCS)
    return f"""
  <datasources>
    <datasource caption='Medicare Cost Drivers' inline='true' name='{DS}' version='18.1'>
      <connection class='federated'>
        <named-connections>
          <named-connection caption='tableau_data' name='{CONN}'>
            <connection class='textscan' directory='Data/output' filename='tableau_data.csv' password='' server='' />
          </named-connection>
        </named-connections>
        <relation connection='{CONN}' name='tableau_data.csv' table='[tableau_data#csv]' type='table'>
          <columns character-set='UTF-8' header='yes' locale='en_US' separator=','>{rel_cols}</columns>
        </relation>
      </connection>
      <aliases enabled='yes' />
      {cols}
      <layout dim-ordering='alphabetic' measure-ordering='alphabetic' show-structure='true' />
    </datasource>
  </datasources>"""

def color_style():
    maps = "".join(f"<map to='{c}'><bucket>&quot;{escape(k)}&quot;</bucket></map>" for k, c in zip(CATS, COLORS))
    return (f"<style><style-rule element='mark'><encoding attr='color' field='{ref('service_category', 'dim')}' "
            f"type='palette'>{maps}</encoding></style-rule></style>")

def demo_filters():
    """Context filters (all values selected) for the three demographic fields."""
    out = ""
    for f in ["dual_status", "age_band", "sex"]:
        out += (f"<filter class='categorical' column='{ref(f, 'dim')}' context='true'>"
                f"<groupfilter function='level-members' level='{inst(f, 'dim')}' user:ui-enumeration='all' "
                f"user:ui-marker='enumerate' /></filter>")
    return out

def member_filter(field, kind, value, is_string=True):
    member = f"&quot;{escape(value)}&quot;" if is_string else value
    return (f"<filter class='categorical' column='{ref(field, kind)}'>"
            f"<groupfilter function='member' level='{inst(field, kind)}' member='{member}' "
            f"user:ui-domain='database' user:ui-enumeration='inclusive' user:ui-marker='enumerate' /></filter>")

def worksheet(name, title, deps, rows, cols, mark, color=None, extra_filters="", slices_extra=(), label=False):
    """deps: list of (field, kind) used on the sheet. Base columns for calcs are added automatically."""
    base = {"dual_status", "age_band", "sex"} | {f for f, _ in deps}
    needed = set(base)
    for f, _ in deps:
        if f.startswith("Calculation_"):
            needed |= {"allowed", "pc_allowed", "ab_mm", "pd_mm", "service_category", "yr", "row_type",
                       "Calculation_mm_ab", "Calculation_mm_pd", "Calculation_denom"}
    col_xml = "".join(column_xml(n) for n in sorted(needed))
    insts = {(f, k) for f, k in deps} | {("dual_status", "dim"), ("age_band", "dim"), ("sex", "dim")}
    inst_xml = "".join(instance_xml(f, k) for f, k in sorted(insts))
    slices = "".join(f"<column>{ref(f, 'dim')}</column>" for f in ["dual_status", "age_band", "sex"])
    slices += "".join(f"<column>{s}</column>" for s in slices_extra)
    enc = f"<encodings><color column='{color}' /></encodings>" if color else ""
    lbl = ("<style><style-rule element='mark'><format attr='mark-labels-show' value='true' /></style-rule></style>"
           if label else "")
    return f"""
    <worksheet name={Q(name)}>
      <layout-options><title><formatted-text><run fontsize='12' bold='true'>{escape(title)}</run></formatted-text></title></layout-options>
      <table>
        <view>
          <datasources><datasource caption='Medicare Cost Drivers' name='{DS}' /></datasources>
          <datasource-dependencies datasource='{DS}'>{col_xml}{inst_xml}</datasource-dependencies>
          {demo_filters()}{extra_filters}
          <slices>{slices}</slices>
          <aggregation value='true' />
        </view>
        {color_style() if color else '<style />'}
        <panes>
          <pane selection-relaxation-option='selection-relaxation-allow'>
            <view><breakdown value='auto' /></view>
            <mark class='{mark}' />
            {enc}
            {lbl}
          </pane>
        </panes>
        <rows>{rows}</rows>
        <cols>{cols}</cols>
      </table>
    </worksheet>"""

def worksheets_xml():
    spend = member_filter("row_type", "dim", "spend")
    s1 = worksheet("PMPM by Category", "Allowed PMPM by Peterson-Milbank service category",
                   [("yr", "ord"), ("service_category", "dim"), ("row_type", "dim"), ("Calculation_pmpm", "calc")],
                   rows=ref("Calculation_pmpm", "calc"), cols=ref("yr", "ord"), mark="Bar",
                   color=ref("service_category", "dim"), extra_filters=spend, slices_extra=[ref("row_type", "dim")])
    s2 = worksheet("Total PMPM Trend", "Total allowed PMPM (medical + pharmacy)",
                   [("yr", "ord"), ("Calculation_total_pmpm", "calc")],
                   rows=ref("Calculation_total_pmpm", "calc"), cols=ref("yr", "ord"), mark="Line", label=True)
    s3 = worksheet("Subcategory PMPM", "PMPM by subcategory, 2022",
                   [("yr", "ord"), ("service_category", "dim"), ("subcategory", "dim"), ("row_type", "dim"),
                    ("Calculation_pmpm", "calc")],
                   rows=f"({ref('service_category', 'dim')} / {ref('subcategory', 'dim')})",
                   cols=ref("Calculation_pmpm", "calc"), mark="Bar", color=ref("service_category", "dim"),
                   extra_filters=spend + member_filter("yr", "ord", "2022", is_string=False),
                   slices_extra=[ref("row_type", "dim"), ref("yr", "ord")], label=True)
    s4 = worksheet("Primary Care Share", "Primary care share of medical spend (Milbank spec)",
                   [("yr", "ord"), ("Calculation_pc_share", "calc")],
                   rows=ref("Calculation_pc_share", "calc"), cols=ref("yr", "ord"), mark="Bar", label=True)
    return "<worksheets>" + s1 + s2 + s3 + s4 + "</worksheets>"

def dashboard_xml():
    z = lambda i, name, x, y, w, h: f"<zone h='{h}' id='{i}' name={Q(name)} w='{w}' x='{x}' y='{y}' />"
    fz = lambda i, param, x, y, w, h: (f"<zone h='{h}' id='{i}' mode='checkdropdown' name='PMPM by Category' "
                                        f"param='{ref(param, 'dim')}' type-v2='filter' w='{w}' x='{x}' y='{y}' />")
    return f"""
  <dashboards>
    <dashboard name='Cost Drivers'>
      <style />
      <size maxheight='900' maxwidth='1400' minheight='900' minwidth='1400' sizing-mode='fixed' />
      <zones>
        <zone h='100000' id='1' type-v2='layout-basic' w='100000' x='0' y='0'>
          <zone h='6000' id='2' type-v2='title' w='100000' x='0' y='0' />
          {fz(3, 'dual_status', 0, 6000, 33333, 7000)}
          {fz(4, 'age_band', 33333, 6000, 33333, 7000)}
          {fz(5, 'sex', 66666, 6000, 33334, 7000)}
          {z(6, 'PMPM by Category', 0, 13000, 60000, 45000)}
          {z(7, 'Total PMPM Trend', 60000, 13000, 40000, 45000)}
          {z(8, 'Subcategory PMPM', 0, 58000, 60000, 42000)}
          {z(9, 'Primary Care Share', 60000, 58000, 40000, 42000)}
        </zone>
      </zones>
    </dashboard>
  </dashboards>"""

def windows_xml():
    ws = "".join(f"<window class='worksheet' name={Q(n)} />" for n in
                 ["PMPM by Category", "Total PMPM Trend", "Subcategory PMPM", "Primary Care Share"])
    return f"<windows source-height='30'>{ws}<window class='dashboard' maximized='true' name='Cost Drivers' /></windows>"

def workbook_xml():
    return f"""<?xml version='1.0' encoding='utf-8' ?>
<workbook original-version='18.1' source-build='2023.1.0 (20231.23.0310.1045)' source-platform='win' version='18.1' xmlns:user='http://www.tableausoftware.com/xml/user'>
  <preferences><preference name='ui.encoding.shelf.height' value='24' /><preference name='ui.shelf.height' value='26' /></preferences>
  {datasource_xml()}
  {worksheets_xml()}
  {dashboard_xml()}
  {windows_xml()}
</workbook>
"""

if __name__ == "__main__":
    xml = workbook_xml()
    import xml.dom.minidom as md
    md.parseString(xml.encode())          # fail fast on malformed XML
    OUT.parent.mkdir(exist_ok=True)
    (OUT.parent / "Medicare Cost Drivers.twb").write_text(xml)   # unpackaged copy, easy to diff
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("Medicare Cost Drivers.twb", xml)
        z.write(CSV, "Data/output/tableau_data.csv")
    print("wrote", OUT.relative_to(ROOT), f"({OUT.stat().st_size / 1024:.0f} KB)")
