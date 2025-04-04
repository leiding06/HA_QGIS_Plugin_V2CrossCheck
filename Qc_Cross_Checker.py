<<<<<<< HEAD

import os
from qgis.utils import iface
import processing
from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QDesktopServices
from qgis.core import QgsProject, QgsSpatialIndex
from datetime import datetime

# 存储错误信息的列表
context_format_errors = [] 
duplicated_context_errors = []  
context_not_match = []  # ✅ Add mismatch storage

# 💕 查找格式错误
def context_format_checker(layers_info):
    for layer_name, field_name, digits in layers_info:
        layers = QgsProject.instance().mapLayersByName(layer_name)
        if not layers:
            iface.messageBar().pushWarning("Context Format Checker", f"⚠️ Layer '{layer_name}' not found.")
            continue

        layer = layers[0]
        field_index = layer.fields().indexFromName(field_name)
        if field_index == -1:
            iface.messageBar().pushWarning("Context Format Checker", f"⚠️ Field '{field_name}' not found in '{layer_name}'.")
            continue

        for feature in layer.getFeatures():
            field_value = str(feature[field_name])
            if len(field_value) != digits:
                context_format_errors.append(f"{layer_name}-{feature['fid']}-{field_name}-{digits}-{feature[field_name]}")

# 💕 查找重复的 Cut_No
def duplicated_context(layers_info):
    for layer_name, field_name in layers_info:
        layers = QgsProject.instance().mapLayersByName(layer_name)
        if not layers:
            iface.messageBar().pushWarning("Duplicated Context", f"⚠️ Layer '{layer_name}' not found.")
            continue

        layer = layers[0]
        field_index = layer.fields().indexFromName(field_name)
        if field_index == -1:
            iface.messageBar().pushWarning("Duplicated Context", f"⚠️ Field '{field_name}' not found in '{layer_name}'.")
            continue

        expression = f'COUNT(1, "{field_name}") > 1'
        processing.run("qgis:selectbyexpression", {'INPUT': layer, 'EXPRESSION': expression, 'METHOD': 0})
        
        unique_duplicated_values = set()
        for feature in layer.selectedFeatures():
            value = feature[field_name]
            if value not in unique_duplicated_values:
                unique_duplicated_values.add(value)

                field_index = layer.fields().indexFromName('Survey Note')
                note = feature[field_index] if field_index != -1 and feature[field_index] and len(str(feature[field_index])) > 1 else ''
                duplicated_context_errors.append(f'{layer_name}-{feature.id()}-{field_name}-{value}-{note}')

        duplicated_context_errors.sort(key=lambda x: (x.split('-')[0], x.split('-')[3]))

# 💕 位置检查（交叉检查 Cut_No 和几何关系）
def location_check(layers_info):
    layer_dict = {}

    for layer_name, field_name, is_compulsory in layers_info:
        layers = QgsProject.instance().mapLayersByName(layer_name)
        if layers:
            layer_dict[layer_name] = {"layer": layers[0], "field": field_name, "compulsory": is_compulsory}
        else:
            iface.messageBar().pushWarning("Family Check", f"⚠️ Layer '{layer_name}' not found.")
            layer_dict[layer_name] = None  # Mark missing layer as None, so we can skip it later

    # Define required layers
    required_layers = ["Excavated", "Cut", "Break of Slope"]
    for req in required_layers:
        if req not in layer_dict or layer_dict[req] is None:
            iface.messageBar().pushWarning("Family Check", f"⚠️ Missing required layer: {req}")

    # Proceed with checking if layers are present, access the actual layer using ["layer"]
    excavated_layer = layer_dict.get("Excavated", {}).get("layer")
    cut_layer = layer_dict.get("Cut", {}).get("layer")
    bos_layer = layer_dict.get("Break of Slope", {}).get("layer")
    section_layer = layer_dict.get("Section", {}).get("layer")

    # Check if layers are missing, if so, initialize empty lists for their data
    if not excavated_layer or not cut_layer or not bos_layer:
        iface.messageBar().pushWarning("Family Check", "One or more required layers are missing. Skipping related checks.")


    for ex_feature in excavated_layer.getFeatures() if excavated_layer else []:
        ex_fid = ex_feature["fid"]
        ex_no = ex_feature[layer_dict["Excavated"]["field"]] if excavated_layer else ''

        cut_match = False
        cut_no = None

        # Check for matching Cut features
        if cut_layer:
            for cut_feature in cut_layer.getFeatures():
                if ex_feature.geometry().contains(cut_feature.geometry()):
                    cut_no = cut_feature[layer_dict["Cut"]["field"]]
                    cut_match = cut_no == ex_no
                    break
        bos_match = False
        bos_count = 0
        bos_no = None
        if bos_layer:
            bos_count = sum(1 for bos_feature in bos_layer.getFeatures() if ex_feature.geometry().contains(bos_feature.geometry()))
            for bos_feature in bos_layer.getFeatures():
                if ex_feature.geometry().contains(bos_feature.geometry()):
                    bos_no = bos_feature[layer_dict["Break of Slope"]["field"]]
                    bos_match = bos_no == ex_no
                    break
        section_match = False
        section_no = "No Section, please check DP"
        if section_layer:
            for section_feature in section_layer.getFeatures():
                if ex_feature.geometry().contains(section_feature.geometry()):
                    section_no = section_feature[layer_dict["Section"]["field"]]
                    section_match =  section_no == ex_no
                    break  

        # Add to mismatch list if there's any issue
        if not cut_match or (bos_count not in [1, 2]) or not bos_match or not section_match:
            context_not_match.append({
                'ex_fid': ex_fid,
                'ex_no':ex_no,
                'cut_no': cut_no,
                'cut_match': "Match" if cut_match else "Mismatch",
                'bos_no':bos_no,
                'bos_match': "Match" if bos_match else "Mismatch",
                'bos_count': "Missing" if not bos_count else bos_count,
                'section_no':section_no,
                'section_match': "Match" if section_match else "No Section/Mismatch"
            })


# 执行数据检查
context_format_checker([
    ('Excavated', 'Cut_No', 6),
    ('Cut', 'Cut_No', 6),
    ('Section', 'Cut_No', 6),
    ('Structure', 'Structure_', 6),
    ('Small Find', 'SF_No', 5),
    ('Sample', 'Sample_No', 5), 
    ('Break of Slope', 'Cut_No', 6)
])

duplicated_context([
    ('Excavated', 'Cut_No'),
    ('Cut', 'Cut_No'),
    ('Section', 'Cut_No'),
    ('Small Find', 'SF_No'),
    ('Sample', 'Sample_No')
])

location_check([
    ("Excavated", "Cut_No", True),
    ("Cut", "Cut_No", True),
    ("Break of Slope", "Cut_No", True),
    ("Section", "Cut_No", False)  
])

# 生成 HTML 文件
site_code = "SiteCode"
download_folder = os.path.join(os.path.expanduser("~"), "Downloads")
if not os.path.exists(download_folder):
    os.makedirs(download_folder)

safe_timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
html_filename = f"{site_code}_V2_QC_report_{safe_timestamp}.html"
html_file_path = os.path.join(download_folder, html_filename)

with open(html_file_path, "w", encoding="utf-8") as f:
    f.write("""
    <html>
    <head>
    <title>QC V2 Report</title>
    <style>
        table {
            border-collapse: collapse;
            margin: auto; /* Center the table */
            table-layout: auto; /* Let column widths adjust */
            max-width: 90%; /* Prevents table from taking full width */
        }
        th, td {
            border: 1px solid black;
            padding: 8px;
            text-align: left;
            white-space: nowrap; /* Prevents text from wrapping */
        }
    </style>
    </head>
    <body>
    """)
    f.write(f"<h1 style='text-align: center;'>{site_code} - Quality Control Report</h1>")

    # 📌 输出格式错误
    if context_format_errors:
        f.write(f"<h2 style='text-align: center;'>Context Format Errors ({len(context_format_errors)})</h2>")
        f.write("<table border='1' style='border-collapse: collapse; max-width: 80%;  margin: auto; table-layout: auto;'>")
 
        f.write("<tr><th>  Layer  </th><th>  fid  </th><th>  Field Name  </th><th>Expected Length</th><th>Current Value</th></tr>")
        
        for error_detail in context_format_errors:
            error_parts = error_detail.split("-")
            layer = error_parts[0]
            fid = error_parts[1]
            field = error_parts[2]
            expected_length = error_parts[3]
            current_value = error_parts[4]
            f.write(f"<tr><td>{layer}</td><td>{fid}</td><td>{field}</td><td>{expected_length}</td><td>{current_value}</td></tr>")

        f.write("</table>")
#duplicated_context_errors.append(f'{layer_name}-{feature.id()}-{field_name}-{feature[field_name]}')
    # 📌 输出重复值错误
    if duplicated_context_errors:
        f.write(f"<h2 style='text-align: center;'>Duplicated Context Error ({len(duplicated_context_errors)})</h2>")
        f.write("<table border='1' style='border-collapse: collapse; width: 50%;'>")
        f.write("<tr><th>Layer</th><th>fid</th><th>Field</th><th>Value</th><th>Survey Note</th></tr>")

        for items in duplicated_context_errors:
            item = items.split("-")
            layer = item[0]
            fid = item[1]
            field = item[2]
            value  = item[3]
            note = item[4]
            f.write(f"<tr><td>{layer}</td><td>{fid}</td><td>{field}</td><td>{value}</td><td>{note}</td><tr>")
        f.write("</table>")
    # 📌 Mismatch Table

    if context_not_match:
        f.write(f"<h2 style='text-align: center;'>Spatial Mismatches ({len(context_not_match)})</h2>")
        f.write("<table border='1'><tr><th>Excavted fid</th><th>Excavted No</th><th>Cut No</th><th>Cut Match</th><th>BOS No</th><th>BOS Match</th><th>BOS Count</th><th>Section No</th><th>Section Match</th></tr>")
        context_not_match.sort(key=lambda x: x['ex_no'])
        for mismatch in context_not_match:
            
            # Instead of using `split()`, directly access the dictionary keys
            f.write(f"<tr><td>{mismatch['ex_no']}</td><td>{mismatch['ex_fid']}</td><td>{mismatch['cut_no']}</td><td>{mismatch['cut_match']}</td><td>{mismatch['bos_no']}</td><td>{mismatch['bos_match']}</td><td>{mismatch['bos_count']}</td><td>{mismatch['section_no']}</td><td>{mismatch['section_match']}</td></tr>")

        f.write("</table>")




    f.write("</body></html>")

# 打开 HTML 文件
if os.path.exists(html_file_path):
    QDesktopServices.openUrl(QUrl.fromLocalFile(html_file_path))
    iface.messageBar().pushMessage("Success", f"Report saved to {html_file_path}", level=0, duration=5)
else:
    iface.messageBar().pushMessage("Error", "Failed to generate HTML report.", level=2, duration=5)
>>>>>>> 208cdb5 (Added the cross check 'Mismatch between families')
