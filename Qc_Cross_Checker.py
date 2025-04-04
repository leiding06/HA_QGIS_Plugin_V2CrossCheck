import os
from qgis.utils import iface
import processing
from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QDesktopServices
from qgis.core import QgsProject
from datetime import datetime

# 存储错误信息的列表
context_format_errors = [] 
duplicated_context_errors = []  # ✅ 改变量名，避免和函数名重复

# 💕 检查字段格式
def context_format_checker(layers_info):
    for layer_name, field_name, digits in layers_info:
        layers = QgsProject.instance().mapLayersByName(layer_name)
        if not layers:
            iface.messageBar().pushWarning("Context format Checker", f"⚠️ Layer '{layer_name}' not found.")
            continue

        layer = layers[0]
        field_index = layer.fields().indexFromName(field_name)
        if field_index == -1:
            iface.messageBar().pushWarning("Context format Checker", f"⚠️ Field '{field_name}' not found in layer '{layer_name}'.")
            continue

        trouble_details = []

        for feature in layer.getFeatures():
            field_value = str(feature[field_name])  # 转换为字符串
            if len(field_value) != digits:


                context_format_errors.append(f"{layer_name}-{feature['fid']}-{field_name}-{digits}-{feature[field_name]}")

# 💕 查找重复的 Cut_No
def duplicated_context(layers_info):
    for layer_name, field_name in layers_info:
        layers = QgsProject.instance().mapLayersByName(layer_name)
        if not layers:
            iface.messageBar().pushWarning("Context format Checker", f"⚠️ Layer '{layer_name}' not found.")
            continue

        layer = layers[0]
        field_index = layer.fields().indexFromName(field_name)
        if field_index == -1:
            iface.messageBar().pushWarning("Context format Checker", f"⚠️ Field '{field_name}' not found in layer '{layer_name}'.")
            continue

        # **使用 QGIS 公式查找重复值**
        expression = f'COUNT(1, "{field_name}") > 1'

        result = processing.run("qgis:selectbyexpression", {
            'INPUT': layer,
            'EXPRESSION': expression,
            'METHOD': 0
        })

        # Store unique duplicated values
        unique_duplicated_values = set()

        for feature in layer.selectedFeatures():
            value = feature[field_name]  # Get the duplicated value
            if value not in unique_duplicated_values:
                unique_duplicated_values.add(value)  # Add to set to ensure uniqueness

                # Get Survey Note if available
                field_index = layer.fields().indexFromName('Survey Note')
                note = feature[field_index] if field_index != -1 and feature[field_index] and len(str(feature[field_index])) > 1 else ''


                duplicated_context_errors.append(f'{layer_name}-{feature.id()}-{field_name}-{value}-{note}')
                # Sort the list based on the duplicated value (3rd element in the string split by '-')
                # Sort by (layer_name, value)
                duplicated_context_errors.sort(key=lambda x: (x.split('-')[0], x.split('-')[3]))


# 🛻 站点代码（可以改成用户输入）
site_code = "SiteCode"

# 生成 HTML 文件路径
download_folder = os.path.join(os.path.expanduser("~"), "Downloads")
if not os.path.exists(download_folder):
    os.makedirs(download_folder)

safe_timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")  # 避免 `:` 影响文件名
html_filename = f"{site_code}_V2_QC_report_{safe_timestamp}.html"
html_file_path = os.path.join(download_folder, html_filename)

# 💕 执行数据检查
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

# 💕 生成 HTML 报告
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

    f.write("</body></html>")

# 💕 打开 HTML 文件
if os.path.exists(html_file_path):
    QDesktopServices.openUrl(QUrl.fromLocalFile(html_file_path))
    iface.messageBar().pushMessage("Success", f"Report saved to {html_file_path}", level=0, duration=5)
else:
    iface.messageBar().pushMessage("Error", "Failed to generate HTML report.", level=2, duration=5)
