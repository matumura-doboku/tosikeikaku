import json

with open(r'c:\Users\gyoru\Desktop\city_lite\grid\messyude-ta001.geojson', 'r', encoding='utf-8') as f:
    data = json.load(f)
    
if data['features']:
    props = data['features'][0]['properties']
    print("Properties found:")
    for key, value in props.items():
        print(f"{key}: {value}")
