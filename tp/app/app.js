// NYC Taxi Pulse — App Logic
// Los textos del resumen JSON se insertan escapados. No vienen del usuario (los genera
// tp/kmeans/cmd/resumen_zonas), pero el visor no asume que nunca traigan HTML: los nombres
// ya llevan '&' y una descripción '<8 mph'.
const esc = (s) => String(s).replace(/[&<>"']/g, (ch) => (
  { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]
));
// Los colores van dentro de un atributo style: solo se acepta #RRGGBB.
const colorSeguro = (c) => (/^#[0-9A-Fa-f]{6}$/.test(c) ? c : '#6B7280');

document.addEventListener('DOMContentLoaded', async () => {
  let geojsonData = null;
  let summaryData = null;
  let map = null;
  let geojsonLayer = null;

  // State
  let currentHour = 12;
  let currentDayType = 'semana'; // 'semana' | 'finde'
  let selectedZoneId = null;
  let isPlaying = false;
  let playInterval = null;
  let activeFilterCluster = null;

  // DOM Elements - Temporal & Story
  const hourSlider = document.getElementById('hourSlider');
  const timeText = document.getElementById('timeText');
  const storyTimeTag = document.getElementById('storyTimeTag');
  const storyText = document.getElementById('storyText');
  const momentBtns = document.querySelectorAll('.moment-btn');
  const btnSemana = document.getElementById('btnSemana');
  const btnFinde = document.getElementById('btnFinde');
  const btnPlay = document.getElementById('btnPlay');
  const playIcon = document.getElementById('playIcon');

  // Filter Elements
  const activeFilterPill = document.getElementById('activeFilterPill');
  const filterColorDot = document.getElementById('filterColorDot');
  const filterLabel = document.getElementById('filterLabel');
  const btnClearFilter = document.getElementById('btnClearFilter');

  // Sheet Elements
  const zoneSheet = document.getElementById('zoneSheet');
  const sheetHandle = document.getElementById('sheetHandle');
  const sheetWelcome = document.getElementById('sheetWelcome');
  const sheetDetail = document.getElementById('sheetDetail');
  const btnCloseDetail = document.getElementById('btnCloseDetail');
  const quickZoneBtns = document.querySelectorAll('.quick-zone-btn');

  // Inspector Detail Elements
  const zoneBorough = document.getElementById('zoneBorough');
  const zoneName = document.getElementById('zoneName');
  const clusterBadge = document.getElementById('clusterBadge');
  const clusterColorDot = document.getElementById('clusterColorDot');
  const clusterName = document.getElementById('clusterName');
  const archetypeDesc = document.getElementById('archetypeDesc');
  const odsCard = document.getElementById('odsCard');
  const speedBadge = document.getElementById('speedBadge');
  const odsRecommendation = document.getElementById('odsRecommendation');
  const statTrips = document.getElementById('statTrips');
  const statDur = document.getElementById('statDur');
  const statDist = document.getElementById('statDist');
  const statDominance = document.getElementById('statDominance');
  const distributionBar = document.getElementById('distributionBar');
  const distributionLegend = document.getElementById('distributionLegend');

  // Tabs & Street Card Elements
  const tabStreet = document.getElementById('tabStreet');
  const tabElena = document.getElementById('tabElena');
  const tabContentStreet = document.getElementById('tabContentStreet');
  const tabContentElena = document.getElementById('tabContentElena');
  const fareEstimate = document.getElementById('fareEstimate');
  const streetTipText = document.getElementById('streetTipText');

  // Modal Elements
  const btnLegend = document.getElementById('btnLegend');
  const legendModal = document.getElementById('legendModal');
  const btnCloseModal = document.getElementById('btnCloseModal');
  const archetypesList = document.getElementById('archetypesList');

  // New HCD Elements (Search, Header Close, Info Modal, Recenter & Guided Tour)
  const btnCloseDetailHeader = document.getElementById('btnCloseDetailHeader');
  const zoneSearchInput = document.getElementById('zoneSearchInput');
  const zoneDatalist = document.getElementById('zoneDatalist');
  const btnInfoModal = document.getElementById('btnInfoModal');
  const infoModal = document.getElementById('infoModal');
  const btnCloseInfoModal = document.getElementById('btnCloseInfoModal');
  const btnHelp = document.getElementById('btnHelp');
  const btnRecenter = document.getElementById('btnRecenter');
  const tourModal = document.getElementById('tourModal');
  const btnCloseTour = document.getElementById('btnCloseTour');
  const btnTourNext = document.getElementById('btnTourNext');
  const btnTourPrev = document.getElementById('btnTourPrev');
  const tourStepBadge = document.getElementById('tourStepBadge');
  const tourStep1 = document.getElementById('tourStep1');
  const tourStep2 = document.getElementById('tourStep2');
  const tourStep3 = document.getElementById('tourStep3');
  const dot1 = document.getElementById('dot1');
  const dot2 = document.getElementById('dot2');
  const dot3 = document.getElementById('dot3');

  // Map Controls & Collapsible Elements
  const appContainer = document.getElementById('app');
  const btnTogglePanels = document.getElementById('btnTogglePanels');
  const btnRestorePanels = document.getElementById('btnRestorePanels');
  const iconEyeOpen = document.querySelector('.icon-eye-open');
  const iconEyeClosed = document.querySelector('.icon-eye-closed');
  const btnMinimizeTemporal = document.getElementById('btnMinimizeTemporal');
  const temporalControls = document.getElementById('temporalControls');

  let currentTourStep = 1;

  // 1. Stories by Hour (Elena's Narrative Guide)
  const hourStories = {
    semana: {
      0: { time: "00:00", text: "Madrugada: Regreso a casa cruzando puentes y salidas tardías de zonas de ocio." },
      1: { time: "01:00", text: "Madrugada: Flujo escaso, viajes largos entre distritos hacia áreas residenciales." },
      2: { time: "02:00", text: "Noche profunda: La ciudad descansa; los taxis atienden zonas con menor frecuencia de metro nocturno." },
      3: { time: "03:00", text: "Noche profunda: Mínimo histórico de viajes en toda la ciudad." },
      4: { time: "04:00", text: "Antes del alba: Movimientos preliminares de trabajadores esenciales y turnos rotativos." },
      5: { time: "05:00", text: "Amanecer: Primeros viajes del día hacia estaciones troncales y terminales aéreas." },
      6: { time: "06:00", text: "Despertar: Comienza a activarse el flujo hacia distritos financieros y corporativos." },
      7: { time: "07:00", text: "Inicio de jornada: Congestión en aumento en los accesos y túneles hacia Manhattan." },
      8: { time: "08:00", text: "Hora punta matutina: Manhattan absorbe viajes corporativos hacia centros de empleo." },
      9: { time: "09:00", text: "Pico matutino: Máxima densidad de tráfico en Midtown y el Distrito Financiero." },
      10: { time: "10:00", text: "Media mañana: Desplazamientos entre reuniones en el núcleo de oficinas." },
      11: { time: "11:00", text: "Antes de almuerzo: Tráfico denso y micro-viajes corporativos de corta distancia." },
      12: { time: "12:00", text: "Mediodía laboral: Almuerzos de negocios y micro-saltos de 1 milla en Manhattan." },
      13: { time: "13:00", text: "Sobremesa: Retorno a oficinas y diligencias rápidas en el centro financiero." },
      14: { time: "14:00", text: "Salidas tempranas: Se forma el corredor vespertino hacia terminales JFK y LaGuardia." },
      15: { time: "15:00", text: "Pico aeroportuario: Máxima demanda de enlaces largos por autopista hacia terminales aéreas." },
      16: { time: "16:00", text: "Tarde: Transición hacia la hora punta de salida; tráfico saturado en avenidas norte-sur." },
      17: { time: "17:00", text: "Salida de oficinas: Desplazamientos masivos hacia estaciones de tren y restaurantes." },
      18: { time: "18:00", text: "Hora punta vespertina: Retorno a residencias y cenas en distritos céntricos." },
      19: { time: "19:00", text: "Cena y esparcimiento: Corredores gastronómicos activos en SoHo, Flatiron y Hell's Kitchen." },
      20: { time: "20:00", text: "Cultura y entretenimiento: Concentración de viajes en Broadway y distritos teatrales." },
      21: { time: "21:00", text: "Inicio nocturno: Ocio nocturno activo en Lower East Side, Williamsburg y Meatpacking." },
      22: { time: "22:00", text: "Noche activa: Traslados de media distancia entre polos gastronómicos y bares." },
      23: { time: "23:00", text: "Noche cerrada: Retornos tardíos hacia distritos exteriores y puentes." }
    },
    finde: {
      0: { time: "00:00", text: "Madrugada de fin de semana: Vida nocturna activa en Meatpacking, SoHo y Lower East Side." },
      1: { time: "01:00", text: "Madrugada de fin de semana: Alta demanda en locales de ocio en Manhattan y Brooklyn." },
      2: { time: "02:00", text: "Cierre de locales: Demanda sostenida de retornos hacia zonas residenciales." },
      3: { time: "03:00", text: "Cierre nocturno: Retornos tardíos por los puentes hacia Queens y Brooklyn." },
      4: { time: "04:00", text: "Madrugada tranquila: La ciudad reduce sensiblemente el volumen de viajes." },
      5: { time: "05:00", text: "Amanecer de fin de semana: Mínimo semanal absoluto de tráfico vehicular." },
      6: { time: "06:00", text: "Amanecer tranquilo: Tráfico fluido orientado principalmente hacia aeropuertos." },
      7: { time: "07:00", text: "Mañana de descanso: Despertar lento y tráfico ligero en toda el área urbana." },
      8: { time: "08:00", text: "Mañana relajada: Viajes recreativos hacia parques, muelles y cafeterías." },
      9: { time: "09:00", text: "Brunch matutino: Movilidad hacia Central Park, Greenwich Village y Brooklyn." },
      10: { time: "10:00", text: "Media mañana recreativa: Central Park, DUMBO y polos peatonales activos." },
      11: { time: "11:00", text: "Mediodía de paseo: Turismo y compras en SoHo, Quinta Avenida y Flatiron." },
      12: { time: "12:00", text: "Paseos de fin de semana: Familias y turistas recorriendo museos y centros culturales." },
      13: { time: "13:00", text: "Tarde de ocio: Turismo activo y gastronomía en distritos históricos." },
      14: { time: "14:00", text: "Tarde comercial: Alta concentración en corredores peatonales y comerciales." },
      15: { time: "15:00", text: "Pico recreativo: Mayor volumen de viajes de placer y esparcimiento de la semana." },
      16: { time: "16:00", text: "Tarde al aire libre: Retorno gradual desde parques, museos y zonas costeras." },
      17: { time: "17:00", text: "Atardecer: Desplazamientos hacia cenas tempranas y espectáculos teatrales." },
      18: { time: "18:00", text: "Cena de fin de semana: Restaurantes y teatros con alta afluencia en Manhattan." },
      19: { time: "19:00", text: "Noche gastronómica: Movilidad sostenida hacia eventos y gastronomía." },
      20: { time: "20:00", text: "Broadway y cultura: Gran concentración en Theatre District y Lincoln Center." },
      21: { time: "21:00", text: "Noche de fin de semana: Vida nocturna activa en todo Lower Manhattan y Brooklyn." },
      22: { time: "22:00", text: "Pico de ocio nocturno: Máxima actividad en bares, coctelerías y música en vivo." },
      23: { time: "23:00", text: "Fiesta de fin de semana: Demanda elevada de traslados urbanos en distritos nocturnos." }
    }
  };

  // Elena's ODS 11 Diagnostics
  const elenaRecommendations = {
    0: { speed: 9.1, text: "<strong>Salida laboral masiva:</strong> Oportunidad de descongestión mediante buses lanzadera y ensanchamiento de veredas en horas punta vespertinas." },
    1: { speed: 10.1, text: "<strong>Demanda recreativa nocturna:</strong> Fomentar paraderos seguros de taxi y extender la frecuencia de trenes del metro en líneas alimentadoras." },
    2: { speed: 9.7, text: "<strong>Alta sustituibilidad (ODS 11.2):</strong> 1 milla en 6 min. Zona prioritaria para ciclovías protegidas (Citi Bike) que reemplacen taxis en micro-trayectos." },
    3: { speed: 8.1, text: "<strong>Fricción severa por congestión (< 8.5 mph):</strong> Justificación empírica directa para el peaje de congestión (Congestion Pricing) y prioridad semafórica para buses." },
    4: { speed: 13.4, text: "<strong>Brecha de red nocturna:</strong> Retornos cruzando puentes hacia Brooklyn/Queens. Revela la necesidad de líneas SBS (Select Bus Service) nocturnas." },
    5: { speed: 20.8, text: "<strong>Corredor troncal masivo:</strong> Fortalecer la conexión ferroviaria JFK AirTrain / LIRR para reducir la dependencia de vehículos particulares por autopista." },
    6: { speed: 8.9, text: "<strong>Movilidad recreativa de fin de semana:</strong> Destinos hacia parques y museos. Implementar corredores peatonales 'Calles Abiertas' (Open Streets)." },
    7: { speed: 9.2, text: "<strong>Micro-desplazamientos de última milla:</strong> Oportunidad de descarbonización mediante micro-movilidad eléctrica compartida." }
  };

  // Marco & Leo's Street Advice and Fare Estimates
  const streetAdvice = {
    0: { fare: "$18 - $24", tip: "<strong>Salida laboral pesada:</strong> Tráfico lento hacia el norte. Pasajero: si vas a menos de 1.5 mi, caminar o Citi Bike te ahorrará 10 min. Conductor: alta demanda continua hacia Upper Manhattan." },
    1: { fare: "$15 - $20", tip: "<strong>Ruta nocturna:</strong> Tráfico fluido entre zonas de ocio (SoHo, Meatpacking, Williamsburg). Conductor: clientela de ocio y flujo rápido de carreras cortas." },
    2: { fare: "$10 - $14", tip: "<strong>Micro-carrera:</strong> Apenas ~1 milla. Pasajero: llegas caminando en 12 minutos y te ahorras $12+. Conductor: bajadas de bandera continuas sin salir del distrito." },
    3: { fare: "$14 - $18", tip: "<strong>Paso de congestión (<8.5 mph):</strong> Midtown saturado al mediodía. Conductor: evitar 5ta y 6ta Ave. Pasajero: el metro (líneas B/D/F/M o N/Q/R) es el doble de rápido." },
    4: { fare: "$28 - $36", tip: "<strong>Cruce de puentes:</strong> Retorno cruzando hacia Brooklyn/Queens. Conductor: buena recaudación, pero considerar el retorno en vacío. Pasajero: ideal para viajes compartidos." },
    5: { fare: "$70 - $85", tip: "<strong>Enlace a aeropuerto:</strong> JFK Tarifa plana (~$70) o taxímetro a LGA. Conductor: alta recaudación en terminales. Pasajero: salir con 50-60 min de margen por autopista." },
    6: { fare: "$15 - $20", tip: "<strong>Paseo de fin de semana:</strong> Destinos hacia Central Park, museos y compras en SoHo. Conductor: turismo familiar con propinas promedio superiores." },
    7: { fare: "$11 - $15", tip: "<strong>Conexión de última milla:</strong> De estaciones troncales (Penn Station/Grand Central) a oficinas. Pasajero: a pie o en bus M42 es veloz si no se lleva equipaje." }
  };

  // High-performance SVG renderer with wide padding (200% margin around viewport)
  // Ensures all NYC polygons stay rendered, painted, and visible during drag gestures
  const svgRenderer = L.svg({ padding: 2.0 });

  // 2. Initialize Map
  function initMap() {
    const nycBounds = L.latLngBounds([40.45, -74.35], [40.96, -73.60]);

    map = L.map('map', {
      center: [40.7350, -73.9500],
      zoom: 11,
      minZoom: 10,
      maxZoom: 16,
      maxBounds: nycBounds,
      maxBoundsViscosity: 0.7,
      renderer: svgRenderer,
      zoomControl: false,
      attributionControl: false,
      inertia: true,
      inertiaDeceleration: 3000,
      fadeAnimation: true,
      zoomAnimation: true
    });
    window.map = map;

    const tileOptions = {
      maxZoom: 16,
      updateWhenIdle: false,   // Crucial on mobile: load tiles during drag instead of waiting for finger release
      updateWhenZooming: true, // Keep updating tiles during zoom
      updateInterval: 80,      // Fast 80ms check while dragging
      keepBuffer: 8            // Preload 8 rows/cols of tiles around viewport
    };

    // Dark Map Layer (Esri Dark Gray - libre, sin marcas de agua)
    L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}', tileOptions).addTo(map);

    // Subtle reference labels
    L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}', {
      ...tileOptions,
      opacity: 0.5
    }).addTo(map);
  }

  // 3. Load Data
  async function loadData() {
    try {
      const [geoRes, sumRes] = await Promise.all([
        fetch('data/nyc_taxi_zones.geojson'),
        fetch('data/nyc_clusters_resumen.json')
      ]);

      geojsonData = await geoRes.json();
      summaryData = await sumRes.json();

      renderGeoJson();
      populateLegendModal();
      populateSearchDatalist();
      updateView();
      checkUrlParams();
    } catch (err) {
      console.error('Error al cargar datos:', err);
    }
  }

  // Populate Autocomplete Search Datalist
  function populateSearchDatalist() {
    if (!geojsonData || !zoneDatalist) return;
    zoneDatalist.innerHTML = '';
    const sorted = [...geojsonData.features].sort((a, b) => 
      a.properties.name.localeCompare(b.properties.name)
    );
    sorted.forEach(feat => {
      const opt = document.createElement('option');
      opt.value = `${feat.properties.name} (${feat.properties.borough})`;
      zoneDatalist.appendChild(opt);
    });
  }

  // Deep-linking via URL parameters (?zone=161&tab=elena&hour=15&day=semana&filter=5)
  function checkUrlParams() {
    const params = new URLSearchParams(window.location.search);
    if (params.has('hour')) {
      const h = parseInt(params.get('hour'), 10);
      if (h >= 0 && h <= 23) {
        currentHour = h;
        hourSlider.value = h;
      }
    }
    if (params.has('day') && (params.get('day') === 'finde' || params.get('day') === 'semana')) {
      currentDayType = params.get('day');
      if (currentDayType === 'finde') {
        btnFinde.classList.add('active');
        btnSemana.classList.remove('active');
      } else {
        btnSemana.classList.add('active');
        btnFinde.classList.remove('active');
      }
    }
    if (params.has('filter')) {
      const f = parseInt(params.get('filter'), 10);
      if (summaryData.clusters[f]) {
        activeFilterCluster = f;
        if (filterColorDot) filterColorDot.style.backgroundColor = summaryData.clusters[f].color;
        filterLabel.textContent = summaryData.clusters[f].nombre;
        activeFilterPill.classList.remove('hidden');
      }
    }
    updateView();

    if (params.has('zone')) {
      const zId = parseInt(params.get('zone'), 10);
      if (geojsonData && geojsonLayer) {
        geojsonLayer.eachLayer(layer => {
          if (layer.feature.properties.id === zId) {
            onZoneSelect(layer.feature, layer);
          }
        });
      }
    }
    if (params.has('tab') && params.get('tab') === 'elena') {
      if (tabElena) tabElena.click();
    }
    if (params.has('min') && temporalControls) {
      temporalControls.classList.add('minimized');
    }
    if (params.has('clean')) {
      toggleCleanMapMode(true);
    }
    if (params.has('modal')) {
      if (params.get('modal') === 'info' && infoModal) {
        infoModal.classList.remove('hidden');
      } else if (params.get('modal') === 'legend' && legendModal) {
        legendModal.classList.remove('hidden');
      } else if (params.get('modal') === 'tour' && tourModal) {
        openTour();
      }
    } else {
      try {
        if (!localStorage.getItem('nyc_taxi_pulse_tour_seen') && !params.has('zone')) {
          openTour();
        }
      } catch (e) {}
    }
  }

  // 4. Render GeoJSON Polygons
  function renderGeoJson() {
    if (geojsonLayer) {
      map.removeLayer(geojsonLayer);
    }

    geojsonLayer = L.geoJSON(geojsonData, {
      renderer: svgRenderer,
      style: getFeatureStyle,
      onEachFeature: (feature, layer) => {
        layer.on({
          click: () => onZoneSelect(feature, layer)
        });
      }
    }).addTo(map);
  }

  // Color & Style Resolver
  function getFeatureStyle(feature) {
    const zoneId = feature.properties.id;
    const info = getZoneHourInfo(zoneId, currentDayType, currentHour);
    const resumen = getZoneDayResumen(zoneId, currentDayType);

    const isSelected = (selectedZoneId === zoneId);

    // Modo Aislamiento: Cuando se filtra por un arquetipo específico
    if (activeFilterCluster !== null) {
      const isDom = (info && info.dom === activeFilterCluster && info.total > 0);
      const count = (info && info.counts) ? (info.counts[activeFilterCluster] || 0) : 0;
      const total = (info && info.total) ? info.total : 0;
      const pct = total > 0 ? (count / total) : 0;
      const cluster = summaryData.clusters[activeFilterCluster];
      const color = cluster ? cluster.color : '#0072B2';

      // Criterio de volumen o concentración real (auditado por Marco y Elena):
      // Si es dominante O volumen absoluto relevante (>=35 viajes) O alta concentración (>=12 viajes y >=18%)
      const isHighVolumeOrDom = isDom || (count >= 35) || (count >= 12 && pct >= 0.18);

      if (isHighVolumeOrDom) {
        return {
          fillColor: color,
          fillOpacity: isSelected ? 1.0 : 0.88,
          color: '#FFFFFF',
          weight: isSelected ? 3.0 : 1.5,
          dashArray: null
        };
      } else if (count > 0) {
        return {
          fillColor: color,
          fillOpacity: isSelected ? 0.65 : 0.32,
          color: 'rgba(255, 255, 255, 0.30)',
          weight: isSelected ? 2.0 : 0.8,
          dashArray: '2, 3'
        };
      } else {
        return {
          fillColor: '#0F172A',
          fillOpacity: isSelected ? 0.35 : 0.08,
          color: 'rgba(255, 255, 255, 0.04)',
          weight: isSelected ? 1.5 : 0.3,
          dashArray: null
        };
      }
    }

    // Modo Normal:
    // Caso 1: La zona tiene viajes activos en este horario (>= 1 viaje)
    if (info && info.total > 0) {
      const cluster = summaryData.clusters[info.dom];
      const color = cluster ? cluster.color : '#0072B2';
      const isLow = info.total < 8;

      return {
        fillColor: color,
        fillOpacity: isSelected ? 0.95 : (isLow ? 0.55 : 0.78),
        color: isSelected ? '#FFFFFF' : 'rgba(255, 255, 255, 0.20)',
        weight: isSelected ? 2.5 : 0.8,
        dashArray: isLow ? '3, 3' : null
      };
    }

    // Caso 2: Sin viajes en esta hora específica, pero con actividad histórica en el tipo de día
    if (resumen && resumen.total > 0) {
      const cluster = summaryData.clusters[resumen.dom];
      const color = cluster ? cluster.color : '#0072B2';

      return {
        fillColor: color,
        fillOpacity: isSelected ? 0.75 : 0.25,
        color: isSelected ? '#FFFFFF' : 'rgba(255, 255, 255, 0.12)',
        weight: isSelected ? 2.0 : 0.5,
        dashArray: '2, 3'
      };
    }

    // Caso 3: Zonas sin viajes registrados en todo el mes
    return {
      fillColor: '#1E293B',
      fillOpacity: isSelected ? 0.6 : 0.35,
      color: isSelected ? '#FFFFFF' : 'rgba(255, 255, 255, 0.10)',
      weight: isSelected ? 2.0 : 0.5,
      dashArray: null
    };
  }

  // Helpers
  function getZoneHourInfo(zoneId, dayType, hour) {
    if (!summaryData || !summaryData.zonas[zoneId]) return null;
    const dayData = summaryData.zonas[zoneId][dayType];
    if (!dayData || !dayData[hour]) return null;
    return dayData[hour];
  }

  function getZoneDayResumen(zoneId, dayType) {
    if (!summaryData || !summaryData.zonas[zoneId]) return null;
    return summaryData.zonas[zoneId][`${dayType}_resumen`];
  }

  // 5. Update View (Slider / Day / Hour change)
  function updateView() {
    // Format Hour text
    const period = currentHour >= 12 ? 'PM' : 'AM';
    const h12 = (currentHour % 12 === 0) ? 12 : (currentHour % 12);
    const hourStr = `${h12.toString().padStart(2, '0')}:00 ${period}`;
    timeText.textContent = hourStr;

    // Update Story of the current hour
    const story = hourStories[currentDayType][currentHour];
    if (story) {
      if (storyTimeTag) storyTimeTag.textContent = story.time || `${currentHour.toString().padStart(2, '0')}:00`;
      storyText.textContent = story.text;
    }

    // Update active moment buttons
    momentBtns.forEach(btn => {
      const h = parseInt(btn.dataset.hour, 10);
      btn.classList.toggle('active', h === currentHour);
    });

    // Refresh polygon colors with smooth transitions
    if (geojsonLayer) {
      geojsonLayer.eachLayer(layer => {
        layer.setStyle(getFeatureStyle(layer.feature));
      });
    }

    // Refresh Inspector if a zone is selected
    if (selectedZoneId !== null) {
      const feat = geojsonData.features.find(f => f.properties.id === selectedZoneId);
      if (feat) renderInspectorDetail(feat);
    }
  }

  // 6. Zone Selection
  function onZoneSelect(feature, layer) {
    selectedZoneId = feature.properties.id;
    if (typeof toggleCleanMapMode === 'function') {
      toggleCleanMapMode(false);
    }

    // Smooth pan leaving room for the bottom card
    map.fitBounds(layer.getBounds(), {
      paddingBottomRight: [0, 220],
      maxZoom: 13,
      animate: true,
      duration: 0.6
    });

    sheetWelcome.style.display = 'none';
    sheetDetail.style.display = 'flex';

    renderInspectorDetail(feature);
    updateView();
  }

  function deselectZone() {
    selectedZoneId = null;
    sheetDetail.style.display = 'none';
    sheetWelcome.style.display = 'block';
    updateView();
  }

  // 7. Render Inspector Detail
  function renderInspectorDetail(feature) {
    const props = feature.properties;
    const info = getZoneHourInfo(props.id, currentDayType, currentHour);
    const resumen = getZoneDayResumen(props.id, currentDayType);

    zoneBorough.textContent = props.borough.toUpperCase();
    zoneName.textContent = props.name;

    // Si no hay viajes a esta hora exacta
    if (!info || info.total === 0) {
      if (resumen && resumen.total > 0) {
        const cluster = summaryData.clusters[resumen.dom];
        clusterBadge.style.display = 'inline-flex';
        clusterBadge.style.borderColor = cluster.color;
        if (clusterColorDot) clusterColorDot.style.backgroundColor = cluster.color;
        clusterName.textContent = `${cluster.nombre} (Habitual)`;
        clusterName.style.color = cluster.color;

        statTrips.textContent = '0';
        statDur.textContent = `${cluster.duracion_min}m`;
        statDist.textContent = `${cluster.distancia_mi}mi`;
        statDominance.textContent = `0%`;

        archetypeDesc.innerHTML = `
          <strong>Sin salidas a las ${timeText.textContent}:</strong> Esta zona no registra viajes en esta hora exacta.<br>
          <em>Su arquetipo habitual para este día es <strong>${esc(cluster.nombre)}</strong> (${resumen.total.toLocaleString()} viajes en el mes).</em>
        `;

        updateStreetTip(resumen.dom);
        updateElenaDiagnostics(resumen.dom);
        renderDistribution(resumen.counts, resumen.total);
        return;
      }

      clusterBadge.style.display = 'none';
      if (odsCard) odsCard.style.display = 'none';
      archetypeDesc.innerHTML = `
        <strong>Zona atendida por Metro MTA y flotas locales:</strong> Esta zona no registra viajes de Yellow Cabs en el mes analizado.<br>
        <em>Los taxis amarillos concentran su servicio en Manhattan y aeropuertos (JFK/LGA). En este sector la movilidad se canaliza principalmente mediante <strong>Metro (MTA)</strong> o flotas locales (Uber/Lyft).</em>
      `;
      statTrips.textContent = '0';
      statDur.textContent = '--';
      statDist.textContent = '--';
      statDominance.textContent = '0%';
      distributionBar.innerHTML = '';
      distributionLegend.innerHTML = '';
      updateStreetTip(null);
      return;
    }

    // Hay viajes activos
    const cluster = summaryData.clusters[info.dom];
    const domCount = info.counts[info.dom];
    const dominancePct = Math.round((domCount / info.total) * 100);

    clusterBadge.style.display = 'inline-flex';
    clusterBadge.style.borderColor = cluster.color;
    if (clusterColorDot) clusterColorDot.style.backgroundColor = cluster.color;
    clusterName.textContent = cluster.nombre;
    clusterName.style.color = cluster.color;

    statTrips.textContent = info.total.toLocaleString();
    statDur.textContent = `${cluster.duracion_min}m`;
    statDist.textContent = `${cluster.distancia_mi}mi`;
    statDominance.textContent = `${dominancePct}%`;

    const isLow = info.total < 8;
    const notaMuestra = isLow ? `<br><small style="color:#D55E00; font-weight:600;">Muestra reducida: ${info.total} viajes/h registrados (InWatch).</small>` : '';

    archetypeDesc.innerHTML = `
      <strong>${esc(cluster.nombre)}:</strong> ${esc(cluster.subtitulo)}.${notaMuestra}<br>
      ${esc(cluster.desc)}
    `;

    updateStreetTip(info.dom);
    updateElenaDiagnostics(info.dom);
    renderDistribution(info.counts, info.total);
  }

  function updateStreetTip(clusterId) {
    if (!fareEstimate || !streetTipText) return;
    if (clusterId === null || clusterId === undefined || !streetAdvice[clusterId]) {
      fareEstimate.textContent = 'Metro $2.90 / App';
      streetTipText.innerHTML = '<strong>Alternativa de transporte:</strong> Utiliza el metro MTA (24/7) o solicita un auto por app (Uber/Lyft). Los Yellow Cabs rara vez circulan vacíos por este cuadrante.';
      return;
    }
    const adv = streetAdvice[clusterId];
    fareEstimate.textContent = adv.fare;
    streetTipText.innerHTML = adv.tip;
  }

  function updateElenaDiagnostics(clusterId) {
    if (!odsCard) return;
    const diag = elenaRecommendations[clusterId];
    if (!diag) {
      odsCard.style.display = 'none';
      return;
    }
    odsCard.style.display = 'block';
    speedBadge.textContent = `~${diag.speed} mph`;
    odsRecommendation.innerHTML = diag.text;
  }

  function renderDistribution(counts, total) {
    distributionBar.innerHTML = '';
    distributionLegend.innerHTML = '';

    counts.forEach((count, idx) => {
      if (count === 0) return;
      const pct = (count / total) * 100;
      const cMeta = summaryData.clusters[idx];

      const seg = document.createElement('div');
      seg.style.width = `${pct}%`;
      seg.style.backgroundColor = cMeta.color;
      seg.title = `${cMeta.nombre}: ${Math.round(pct)}%`;
      distributionBar.appendChild(seg);

      if (pct >= 8) {
        const legItem = document.createElement('div');
        legItem.className = 'dist-legend-item';
        legItem.innerHTML = `
          <span class="dist-color-box" style="background: ${colorSeguro(cMeta.color)};"></span>
          <span>${esc(cMeta.nombre)} (${Math.round(pct)}%)</span>
        `;
        distributionLegend.appendChild(legItem);
      }
    });
  }

  // 8. Event Listeners
  hourSlider.addEventListener('input', (e) => {
    currentHour = parseInt(e.target.value, 10);
    updateView();
  });

  // Moment Chips Click
  momentBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      currentHour = parseInt(btn.dataset.hour, 10);
      hourSlider.value = currentHour;
      updateView();
    });
  });

  // Quick Zones Click
  quickZoneBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const zId = parseInt(btn.dataset.zone, 10);
      if (!geojsonData || !geojsonLayer) return;

      geojsonLayer.eachLayer(layer => {
        if (layer.feature.properties.id === zId) {
          onZoneSelect(layer.feature, layer);
        }
      });
    });
  });

  if (btnCloseDetail) {
    btnCloseDetail.addEventListener('click', deselectZone);
  }

  if (btnCloseDetailHeader) {
    btnCloseDetailHeader.addEventListener('click', deselectZone);
  }

  // Zone Search Input Listener
  if (zoneSearchInput) {
    zoneSearchInput.addEventListener('change', (e) => {
      const query = e.target.value.trim().toLowerCase();
      if (!query || !geojsonData || !geojsonLayer) return;

      const found = geojsonData.features.find(f => {
        const full = `${f.properties.name} (${f.properties.borough})`.toLowerCase();
        return full === query || f.properties.name.toLowerCase() === query || full.includes(query);
      });

      if (found) {
        geojsonLayer.eachLayer(layer => {
          if (layer.feature.properties.id === found.properties.id) {
            onZoneSelect(layer.feature, layer);
          }
        });
        zoneSearchInput.value = '';
      }
    });
  }

  // Info Modal Listeners (Elena & Rigor)
  if (btnInfoModal && infoModal) {
    btnInfoModal.addEventListener('click', () => {
      infoModal.classList.remove('hidden');
    });
  }
  if (btnCloseInfoModal && infoModal) {
    btnCloseInfoModal.addEventListener('click', () => {
      infoModal.classList.add('hidden');
    });
    infoModal.addEventListener('click', (e) => {
      if (e.target === infoModal) {
        infoModal.classList.add('hidden');
      }
    });
  }

  // Onboarding Tour Logic
  function showTourStep(step) {
    currentTourStep = step;
    if (tourStepBadge) tourStepBadge.textContent = `PASO ${step} DE 3`;
    if (tourStep1) tourStep1.classList.toggle('hidden', step !== 1);
    if (tourStep2) tourStep2.classList.toggle('hidden', step !== 2);
    if (tourStep3) tourStep3.classList.toggle('hidden', step !== 3);

    if (dot1) dot1.classList.toggle('active', step === 1);
    if (dot2) dot2.classList.toggle('active', step === 2);
    if (dot3) dot3.classList.toggle('active', step === 3);

    if (btnTourPrev) btnTourPrev.classList.toggle('hidden', step === 1);
    if (btnTourNext) btnTourNext.textContent = (step === 3) ? 'Comenzar exploración' : 'Siguiente →';
  }

  function closeTour() {
    if (tourModal) tourModal.classList.add('hidden');
    try {
      localStorage.setItem('nyc_taxi_pulse_tour_seen', 'true');
    } catch(e) {}
  }

  function openTour() {
    showTourStep(1);
    if (tourModal) tourModal.classList.remove('hidden');
  }

  if (btnHelp) btnHelp.addEventListener('click', openTour);
  if (btnCloseTour) btnCloseTour.addEventListener('click', closeTour);
  if (btnTourNext) {
    btnTourNext.addEventListener('click', () => {
      if (currentTourStep < 3) {
        showTourStep(currentTourStep + 1);
      } else {
        closeTour();
      }
    });
  }
  if (btnTourPrev) {
    btnTourPrev.addEventListener('click', () => {
      if (currentTourStep > 1) {
        showTourStep(currentTourStep - 1);
      }
    });
  }
  if (tourModal) {
    tourModal.addEventListener('click', (e) => {
      if (e.target === tourModal) closeTour();
    });
  }

  // Recenter Map in Manhattan
  if (btnRecenter) {
    btnRecenter.addEventListener('click', () => {
      map.setView([40.7350, -73.9500], 11, { animate: true, duration: 0.6 });
    });
  }

  // Toggle Clean Map Mode (ocultar menú superior y controles para vista completa)
  function toggleCleanMapMode(forceClean) {
    if (!appContainer) return;
    const shouldClean = (forceClean !== undefined) ? forceClean : !appContainer.classList.contains('clean-map-mode');
    appContainer.classList.toggle('clean-map-mode', shouldClean);
    if (btnRestorePanels) btnRestorePanels.classList.toggle('hidden', !shouldClean);
    if (iconEyeOpen && iconEyeClosed) {
      iconEyeOpen.classList.toggle('hidden', shouldClean);
      iconEyeClosed.classList.toggle('hidden', !shouldClean);
    }
    if (btnTogglePanels) {
      btnTogglePanels.setAttribute('title', shouldClean ? 'Mostrar menú y controles' : 'Ocultar paneles');
    }
  }

  if (btnTogglePanels) {
    btnTogglePanels.addEventListener('click', () => toggleCleanMapMode());
  }

  if (btnRestorePanels) {
    btnRestorePanels.addEventListener('click', () => toggleCleanMapMode(false));
  }

  // Minimize / Expand Temporal Controls Deck
  if (btnMinimizeTemporal && temporalControls) {
    btnMinimizeTemporal.addEventListener('click', (e) => {
      e.stopPropagation();
      temporalControls.classList.toggle('minimized');
      const isMin = temporalControls.classList.contains('minimized');
      btnMinimizeTemporal.setAttribute('title', isMin ? 'Expandir' : 'Minimizar');
      btnMinimizeTemporal.setAttribute('aria-label', isMin ? 'Expandir controles de tiempo' : 'Minimizar controles de tiempo');
    });
  }

  // Mobile Touch Swipe Gestures on Bottom Sheet Handle
  if (sheetHandle) {
    let startY = 0;
    sheetHandle.addEventListener('touchstart', (e) => {
      startY = e.touches[0].clientY;
    }, { passive: true });

    sheetHandle.addEventListener('touchend', (e) => {
      const endY = e.changedTouches[0].clientY;
      const diffY = endY - startY;
      if (diffY > 40) {
        // Swiped down
        if (zoneSheet.classList.contains('expanded')) {
          zoneSheet.classList.remove('expanded');
        } else if (selectedZoneId !== null) {
          deselectZone();
        }
      } else if (diffY < -40) {
        // Swiped up
        zoneSheet.classList.add('expanded');
      }
    }, { passive: true });
  }

  // Toggle bottom sheet expansion on handle click
  if (sheetHandle) {
    sheetHandle.addEventListener('click', () => {
      zoneSheet.classList.toggle('expanded');
    });
  }

  // Tab switching: Street Tip vs Elena ODS 11
  if (tabStreet && tabElena) {
    tabStreet.addEventListener('click', () => {
      tabStreet.classList.add('active');
      tabElena.classList.remove('active');
      tabContentStreet.classList.remove('hidden');
      tabContentElena.classList.add('hidden');
    });

    tabElena.addEventListener('click', () => {
      tabElena.classList.add('active');
      tabStreet.classList.remove('active');
      tabContentElena.classList.remove('hidden');
      tabContentStreet.classList.add('hidden');
    });
  }

  btnSemana.addEventListener('click', () => {
    btnSemana.classList.add('active');
    btnFinde.classList.remove('active');
    currentDayType = 'semana';
    updateView();
  });

  btnFinde.addEventListener('click', () => {
    btnFinde.classList.add('active');
    btnSemana.classList.remove('active');
    currentDayType = 'finde';
    updateView();
  });

  btnPlay.addEventListener('click', () => {
    isPlaying = !isPlaying;
    if (isPlaying) {
      btnPlay.classList.add('playing');
      playIcon.textContent = '⏸';
      playInterval = setInterval(() => {
        currentHour = (currentHour + 1) % 24;
        hourSlider.value = currentHour;
        updateView();
      }, 850);
    } else {
      btnPlay.classList.remove('playing');
      playIcon.textContent = '▶';
      clearInterval(playInterval);
    }
  });

  // Clear Filter Button
  if (btnClearFilter) {
    btnClearFilter.addEventListener('click', (e) => {
      e.stopPropagation();
      activeFilterCluster = null;
      activeFilterPill.classList.add('hidden');
      updateView();
      populateLegendModal();
    });
  }

  // Modal Legend
  btnLegend.addEventListener('click', () => {
    legendModal.classList.remove('hidden');
  });

  btnCloseModal.addEventListener('click', () => {
    legendModal.classList.add('hidden');
  });

  legendModal.addEventListener('click', (e) => {
    if (e.target === legendModal) {
      legendModal.classList.add('hidden');
    }
  });

  // Populate Legend Modal
  function populateLegendModal() {
    if (!summaryData) return;
    archetypesList.innerHTML = '';

    summaryData.clusters.forEach(c => {
      const card = document.createElement('div');
      const isSelected = (activeFilterCluster === c.id);
      card.className = `archetype-card ${isSelected ? 'active-filter' : ''}`;
      card.innerHTML = `
        <div class="arch-header">
          <div class="arch-title-group">
            <span class="arch-color-badge" style="background: ${colorSeguro(c.color)};"></span>
            <span class="arch-name">${esc(c.nombre)}</span>
          </div>
          <span class="arch-pct">${c.porcentaje}% (${c.viajes_total.toLocaleString()})</span>
        </div>
        <p class="arch-desc">${esc(c.desc)}</p>
        <div class="arch-metrics">
          <span>Duración: ~${c.duracion_min} min</span>
          <span>Distancia: ~${c.distancia_mi} mi</span>
          <span>Pico: ~${Math.round(c.hora_pico)}:00 (${esc(c.dia_nombre)})</span>
        </div>
        <div style="font-size: 10.5px; color: ${isSelected ? '#38BDF8' : '#6B7280'}; margin-top: 4px; font-weight: 600;">
          ${isSelected ? 'Activo en el mapa (toca para quitar)' : 'Toca para aislar en el mapa'}
        </div>
      `;

      card.addEventListener('click', () => {
        if (activeFilterCluster === c.id) {
          activeFilterCluster = null;
          activeFilterPill.classList.add('hidden');
        } else {
          activeFilterCluster = c.id;
          if (filterColorDot) filterColorDot.style.backgroundColor = c.color;
          filterLabel.textContent = c.nombre;
          activeFilterPill.classList.remove('hidden');
        }
        legendModal.classList.add('hidden');
        populateLegendModal();
        updateView();
      });

      archetypesList.appendChild(card);
    });
  }

  // Start
  initMap();
  loadData();
});
