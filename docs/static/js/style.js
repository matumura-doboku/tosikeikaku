function getColor(value, min, max, hueStart, hueEnd) {
    if (value === null || value === undefined || value === 0) return 'transparent';
    if (max === min) return `hsl(${hueEnd}, 70%, 50%)`;

    let ratio = (value - min) / (max - min);
    if (ratio < 0) ratio = 0;
    if (ratio > 1) ratio = 1;

    if (hueStart === hueEnd) {
        const l = 90 - (ratio * 50); // 90 -> 40
        return `hsl(${hueStart}, 70%, ${l}%)`;
    }

    const h = hueStart + (ratio * (hueEnd - hueStart));
    return `hsl(${h}, 70%, 50%)`;
}

function getFeatureStyle(feature) {
    const id = feature.properties.id || feature.id;
    const isSelected = selectedGridIds.has(id);
    const isPink = pinkGridIds.has(id);
    const isActive = id === activePopupGridId;

    if (isActive) {
        return {
            color: 'gray',
            weight: 2,
            fillOpacity: 0.5,
            fillColor: 'gray'
        };
    }

    let fillColor = 'blue';
    let fillOpacity = 0.1;
    let strokeColor = 'blue';
    let weight = 1;

    if (currentVizMode !== 'none') {
        let val = 0;
        let min = 0;
        let max = 100;
        let hue = 0;

        if (currentVizMode === 'pop_total') {
            val = feature.properties.POP_TOTAL;
            min = statsRanges.pop_total.min;
            max = statsRanges.pop_total.max;
            hue = 0;
        } else if (currentVizMode === 'ratio_65_over') {
            val = feature.properties.VAL_RATIO_65_OVER;
            min = statsRanges.ratio_65_over.min;
            max = statsRanges.ratio_65_over.max;
            hue = 270;
        } else if (currentVizMode === 'ratio_15_64') {
            val = feature.properties.VAL_RATIO_15_64;
            min = statsRanges.ratio_15_64.min;
            max = statsRanges.ratio_15_64.max;
            hue = 120;
        } else if (currentVizMode === 'traffic_flow') {
            const res = simulationResults[id];
            val = res ? res.flow_Total : 0;
            min = 0;
            max = statsRanges.traffic_flow.max;
            hue = 0;
        } else if (currentVizMode === 'land_price_sim') {
            const res = cityResults[feature.properties.KEY_CODE];
            val = res ? res.land_price : 0;
            min = statsRanges.land_price.min;
            max = statsRanges.land_price.max;
            hue = 60;
            if (val > 0) {
                const r = (val - min) / (max - min || 1);
                hue = 60 - (r * 60);
                return {
                    color: strokeColor,
                    weight: weight,
                    fillColor: `hsl(${hue}, 100%, 50%)`,
                    fillOpacity: 0.6
                };
            }
        } else if (currentVizMode === 'pop_sim') {
            const res = cityResults[feature.properties.KEY_CODE];
            val = res ? res.population : 0;
            min = 0;
            max = statsRanges.pop_sim.max;
            hue = 200;
        } else if (currentVizMode === 'vacant_floor_area_rate') {
            val = feature.properties.VACANT_FLOOR_AREA_RATE;
            min = statsRanges.vacant_floor_area_rate.min;
            max = statsRanges.vacant_floor_area_rate.max;
            hue = 240;
        }

        fillColor = getColor(val, min, max, hue, hue);
        fillOpacity = (val > 0) ? 0.6 : 0.0;
        strokeColor = 'none';
        weight = 0;
    }

    if (isPink) {
        fillOpacity = 0.0;
        strokeColor = '#FF69B4';
        weight = 2;
    }

    if (isSelected) {
        strokeColor = 'green';
        weight = 3;
    }

    return {
        color: strokeColor,
        weight: weight,
        fillColor: fillColor,
        fillOpacity: fillOpacity
    };
}

function updateLegend() {
    if (currentVizMode === 'none') {
        legendDiv.style.display = 'none';
        return;
    }

    let min, max, hue, label;
    if (currentVizMode === 'pop_total') {
        min = statsRanges.pop_total.min;
        max = statsRanges.pop_total.max;
        hue = 0;
        label = '人口総数';
    } else if (currentVizMode === 'ratio_65_over') {
        min = statsRanges.ratio_65_over.min;
        max = statsRanges.ratio_65_over.max;
        hue = 270;
        label = '老年人口比率(65+)';
    } else if (currentVizMode === 'ratio_15_64') {
        min = statsRanges.ratio_15_64.min;
        max = statsRanges.ratio_15_64.max;
        hue = 120;
        label = '生産年齢人口比率(15-64)';
    } else if (currentVizMode === 'traffic_flow') {
        min = 0;
        max = statsRanges.traffic_flow.max;
        hue = 0;
        label = 'Traffic Volume (Veh/Hr)';
    } else if (currentVizMode === 'land_price_sim') {
        min = statsRanges.land_price.min;
        max = statsRanges.land_price.max;
        hue = 60;
        label = 'Land Price (Simulated)';
    } else if (currentVizMode === 'pop_sim') {
        min = 0;
        max = statsRanges.pop_sim.max;
        hue = 200;
        label = 'Population (Simulated)';
    } else if (currentVizMode === 'vacant_floor_area_rate') {
        min = statsRanges.vacant_floor_area_rate.min;
        max = statsRanges.vacant_floor_area_rate.max;
        hue = 240;
        label = '空き床面積率(%)';
    }

    legendDiv.innerHTML = `
        <strong>${label}</strong>
        <div class="legend-gradient" style="background: linear-gradient(to right, hsl(${hue}, 70%, 90%), hsl(${hue}, 70%, 40%));"></div>
        <div class="legend-labels">
            <span>${Math.round(min)}</span>
            <span>${Math.round(max)}</span>
        </div>
    `;
    legendDiv.style.display = 'block';
}
