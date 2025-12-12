import json

geojson_path = r'c:\Users\gyoru\Desktop\city_lite\grid\messyude-ta001.geojson'
with open(geojson_path, 'r', encoding='utf-8') as f:
    data = json.load(f)
    print(list(data['features'][0]['properties'].keys()))
