// Shared DOM references
const addressInput = document.getElementById('address-input');
const suggestionList = document.getElementById('suggestion-list');
const gridToggle = document.getElementById('grid-toggle');
const rangeSelectBtn = document.getElementById('range-select-btn');
const mapContainer = document.getElementById('map');
const propertyPanel = document.getElementById('property-panel');
const propertyContent = document.getElementById('property-content');
const closePropertyPanelBtn = document.getElementById('close-property-panel');
const vizModeSelect = document.getElementById('viz-mode');
const legendDiv = document.getElementById('legend');

const runSimBtn = document.getElementById('run-simulation-btn');
const simStatus = document.getElementById('simulation-status');
const flowMaxSlider = document.getElementById('flow-max-slider');
const flowMaxValSpan = document.getElementById('flow-max-val');

const initCityBtn = document.getElementById('init-city-btn');
const stepCityBtn = document.getElementById('step-city-btn');
const resetCityBtn = document.getElementById('reset-city-btn');
const cityStatus = document.getElementById('city-status');
const stepYearsSelect = document.getElementById('step-years');
const cityYearLabel = document.getElementById('city-year-label');

const reportTabBtn = document.querySelector('.tab-btn[data-tab="report"]');
const reportContentDiv = document.getElementById('report-tab');

// Map instance (initialized in map.js)
let map;

// Shared state
let gridLayer = null;
let isSelectionMode = false;
let selectedGridIds = new Set();
let activePopupGridId = null;
let currentVizMode = 'none';

let statsRanges = {
    'pop_total': { min: 0, max: 0 },
    'ratio_65_over': { min: 0, max: 0 },
    'ratio_15_64': { min: 0, max: 0 },
    'ratio_15_64': { min: 0, max: 0 },
    'traffic_flow': { min: 0, max: 1000 },
    'land_price': { min: 10, max: 20 },
    'pop_sim': { min: 0, max: 100 },
    'vacant_floor_area_rate': { min: 0, max: 100 }
};

let simulationResults = {};
let cityResults = {};
let cityYear = 0;

let pinkGridIds = new Set(); // Range highlight
let analysisOverlays = [];   // Roads / borders overlays

// Property labels (fixed from garbled characters)
const PROPERTY_LABELS = {
    KEY_CODE: 'Key Code',
    MESH1_ID: 'Mesh 1 ID',
    MESH2_ID: 'Mesh 2 ID',
    MESH3_ID: 'Mesh 3 ID',
    MESH4_ID: 'Mesh 4 ID',
    OBJ_ID: 'Object ID',
    gml_id: 'GML ID',
    POP_TOTAL: '莠ｺ蜿｣邱乗焚',
    POP_MALE: '莠ｺ蜿｣・育塙・・,
    POP_FEMALE: '莠ｺ蜿｣・亥･ｳ・・,
    RATIO_0_14: '蟷ｴ蟆台ｺｺ蜿｣豈皮紫(0-14)',
    RATIO_15_64: '逕溽肇蟷ｴ鮨｢莠ｺ蜿｣豈皮紫(15-64)',
    RATIO_65_OVER: '閠∝ｹｴ莠ｺ蜿｣豈皮紫(65+)',
    FLOOR_AREA: '蠎企擇遨・緕｡)',
    VACANT_FLOOR_AREA: '遨ｺ縺榊ｺ企擇遨・緕｡)',
    VACANT_FLOOR_AREA_RATE: '遨ｺ縺榊ｺ企擇遨咲紫(%)'
};
