// NYC Taxi Pulse — App Logic
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
  const storyIcon = document.getElementById('storyIcon');
  const storyText = document.getElementById('storyText');
  const momentBtns = document.querySelectorAll('.moment-btn');
  const btnSemana = document.getElementById('btnSemana');
  const btnFinde = document.getElementById('btnFinde');
  const btnPlay = document.getElementById('btnPlay');
  const playIcon = document.getElementById('playIcon');

  // Filter Elements
  const activeFilterPill = document.getElementById('activeFilterPill');
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
  const clusterIcon = document.getElementById('clusterIcon');
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

  let currentTourStep = 1;

  // 1. Stories by Hour (Elena's Narrative Guide)
  const hourStories = {
    semana: {
      0: { icon: "🌙", text: "Madrugada (00h): Regreso a casa cruzando puentes y salidas tardías de bares." },
      1: { icon: "🌙", text: "Madrugada (01h): Flujo escaso, viajes largos entre distritos hacia residencias." },
      2: { icon: "🌙", text: "Noche profunda (02h): La ciudad descansa; los taxis atienden zonas sin metro nocturno." },
      3: { icon: "🌙", text: "Noche profunda (03h): Mínimo histórico de viajes en toda la ciudad." },
      4: { icon: "🌙", text: "Antes del alba (04h): Movimientos preliminares de trabajadores esenciales y guardias." },
      5: { icon: "✈️", text: "Amanecer (05h): Primeros viajes del día hacia estaciones y aeropuertos." },
      6: { icon: "☕", text: "Despertar (06h): Comienza a activarse el flujo hacia oficinas de Manhattan." },
      7: { icon: "☕", text: "Inicio de jornada (07h): Congestión en aumento en las entradas a la isla." },
      8: { icon: "💼", text: "Hora punta matutina (08h): Manhattan se inunda de viajes corporativos y oficinas." },
      9: { icon: "💼", text: "Pico matutino (09h): Máxima actividad en Midtown y el Distrito Financiero." },
      10: { icon: "💼", text: "Media mañana (10h): Desplazamientos entre reuniones en el centro de Manhattan." },
      11: { icon: "🥪", text: "Antes de almuerzo (11h): Tráfico denso y micro-viajes corporativos." },
      12: { icon: "🥪", text: "Mediodía (12h): Almuerzos de trabajo; muchos micro-saltos de 1 milla en Manhattan." },
      13: { icon: "🥪", text: "Sobremesa (13h): Retorno a oficinas y diligencias rápidas en el centro." },
      14: { icon: "✈️", text: "Primeros vuelos (14h): Comienza a formarse el flujo vespertino hacia JFK y LaGuardia." },
      15: { icon: "✈️", text: "Pico de aeropuerto (15h): Alta demanda de viajes largos por autopista hacia terminales." },
      16: { icon: "🌇", text: "Tarde (16h): Transición hacia la hora punta de salida; tráfico en arterias clave." },
      17: { icon: "🌇", text: "Salida de oficinas (17h): Oficinas vaciándose hacia trenes, buses y restaurantes." },
      18: { icon: "🌇", text: "Hora punta vespertina (18h): Retorno a hogares y cenas en Manhattan." },
      19: { icon: "🍽️", text: "Cena & Relax (19h): Gastronomía activa en Soho, Flatiron y Hell's Kitchen." },
      20: { icon: "🎭", text: "Cultura & Ocio (20h): Movilidad hacia teatros de Broadway y restaurantes." },
      21: { icon: "🍸", text: "Inicio nocturno (21h): Bares y vida nocturna en Lower East Side y Brooklyn." },
      22: { icon: "🍸", text: "Noche de bares (22h): Viajes de media distancia entre locales de ocio." },
      23: { icon: "🍸", text: "Noche activa (23h): Salidas nocturnas y retornos hacia otros distritos." }
    },
    finde: {
      0: { icon: "🍸", text: "Madrugada de fiesta (00h): Vida nocturna en su apogeo en Meatpacking y Soho." },
      1: { icon: "🍸", text: "Madrugada de fiesta (01h): Bares de Lower East Side y Williamsburg colmados." },
      2: { icon: "🍸", text: "Salida de discotecas (02h): Gran demanda de taxis para volver a casa." },
      3: { icon: "🌙", text: "Cierre nocturno (03h): Retornos tardíos por los puentes hacia Queens y Brooklyn." },
      4: { icon: "🌙", text: "Calma de fin de semana (04h): La ciudad finalmente baja el ritmo." },
      5: { icon: "🌙", text: "Amanecer de fin de semana (05h): Mínimo absoluto de tráfico del fin de semana." },
      6: { icon: "☕", text: "Amanecer tranquilo (06h): Pocos viajes, principalmente aeropuertos." },
      7: { icon: "☕", text: "Mañana de descanso (07h): Despertar lento en la ciudad." },
      8: { icon: "☕", text: "Mañana relajada (08h): Viajes hacia parques y cafeterías de barrio." },
      9: { icon: "🥐", text: "Hora de brunch (09h): Comienza la movilidad hacia cafeterías y Central Park." },
      10: { icon: "🥐", text: "Brunch y paseos (10h): Central Park, Greenwich Village y DUMBO activos." },
      11: { icon: "☀️", text: "Mediodía de paseo (11h): Compras en SoHo y paseos familiares." },
      12: { icon: "☀️", text: "Paseos de fin de semana (12h): Familias y turistas recorriendo museos." },
      13: { icon: "☀️", text: "Tarde de ocio (13h): Turismo activo y restaurantes en toda la isla." },
      14: { icon: "☀️", text: "Tarde de compras (14h): Mucha actividad en 5th Avenue y Broadway." },
      15: { icon: "☀️", text: "Pico recreativo (15h): El momento con más viajes de placer de la semana." },
      16: { icon: "☀️", text: "Tarde al aire libre (16h): Regreso de parques y museos." },
      17: { icon: "🌇", text: "Atardecer (17h): Preparación para cenas y espectáculos nocturnos." },
      18: { icon: "🍽️", text: "Cena de fin de semana (18h): Restaurantes llenos en Manhattan y Brooklyn." },
      19: { icon: "🍽️", text: "Noche gastronómica (19h): Traslados hacia eventos y cenas de fin de semana." },
      20: { icon: "🎭", text: "Broadway y cultura (20h): Alta concentración en el Theatre District." },
      21: { icon: "🍸", text: "La noche arranca (21h): Vida nocturna activa en todo Lower Manhattan." },
      22: { icon: "🍸", text: "Pico de ocio (22h): Máxima actividad en bares, coctelerías y música en vivo." },
      23: { icon: "🍸", text: "Fiesta de fin de semana (23h): Calles llenas de taxis en zonas nocturnas." }
    }
  };

  // Elena's ODS 11 Diagnostics
  const elenaRecommendations = {
    0: { speed: 9.1, text: "Salida laboral masiva. Oportunidad de descongestión mediante buses lanzadera y ensanchamiento de veredas en horas punta vespertinas." },
    1: { speed: 10.1, text: "Demanda recreativa nocturna. Fomentar paraderos seguros de taxi y extender la frecuencia de trenes del metro en líneas alimentadoras." },
    2: { speed: 9.7, text: "🎯 <strong>Alta sustituibilidad (ODS 11.2):</strong> 1 milla en 6 min. Zona prioritaria para ciclovías protegidas (Citi Bike) que reemplacen taxis en micro-trayectos." },
    3: { speed: 8.1, text: "⚠️ <strong>Fricción severa por congestión (< 8.5 mph):</strong> Justificación empírica directa para el peaje de congestión (Congestion Pricing) y prioridad semafórica para buses." },
    4: { speed: 13.4, text: "🌙 <strong>Brecha de red nocturna:</strong> Retornos cruzando puentes hacia Brooklyn/Queens. Revela la necesidad de líneas SBS (Select Bus Service) nocturnas." },
    5: { speed: 20.8, text: "✈️ <strong>Corredor troncal masivo:</strong> Fortalecer la conexión ferroviaria JFK AirTrain / LIRR para reducir la dependencia de vehículos particulares por autopista." },
    6: { speed: 8.9, text: "Movilidad recreativa de fin de semana hacia parques y museos. Implementar corredores peatonales 'Calles Abiertas' (Open Streets)." },
    7: { speed: 9.2, text: "🎯 <strong>Micro-desplazamientos de última milla:</strong> Oportunidad de descarbonización mediante micro-movilidad eléctrica compartida." }
  };

  // Marco & Leo's Street Advice and Fare Estimates
  const streetAdvice = {
    0: { fare: "$18 - $24", tip: "🚗 <strong>Salida laboral pesada:</strong> Tráfico lento hacia el norte. Pasajero: si vas a menos de 1.5 mi, caminar o Citi Bike te ahorrará 10 min. Conductor: alta demanda continua hacia Upper Manhattan." },
    1: { fare: "$15 - $20", tip: "🍸 <strong>Ruta nocturna:</strong> Tráfico fluido entre zonas de ocio (SoHo, Meatpacking, Williamsburg). Conductor: clientela de buen humor y flujo rápido de carreras cortas." },
    2: { fare: "$10 - $14", tip: "⚡ <strong>Micro-carrera:</strong> Apenas ~1 milla. Pasajero: llegas caminando en 12 minutos y te ahorras $12+. Conductor: bajadas de bandera continuas sin salir del distrito." },
    3: { fare: "$14 - $18", tip: "🐢 <strong>Paso de tortuga (<8.5 mph):</strong> Midtown colapsado al mediodía. Conductor: evita la 5ta y 6ta Ave. Pasajero: el metro (líneas B/D/F/M o N/Q/R) es el doble de rápido." },
    4: { fare: "$28 - $36", tip: "🌉 <strong>Cruce de puentes:</strong> Retorno cruzando hacia Brooklyn/Queens. Conductor: buena recaudación, pero ojo con volver vacío ('deadheading'). Pasajero: ideal para compartir con amigos." },
    5: { fare: "$70 - $85", tip: "✈️ <strong>Carrera estrella a Aeropuerto:</strong> JFK Tarifa plana (~$70) o taxímetro a LGA. Conductor: alta propina en terminales. Pasajero: sal con 50-60 min de margen por la Van Wyck / BQE." },
    6: { fare: "$15 - $20", tip: "🌳 <strong>Paseo de fin de semana:</strong> Destinos hacia Central Park, museos y compras en SoHo. Conductor: turismo familiar con propinas promedio superiores (~20%)." },
    7: { fare: "$11 - $15", tip: "🚶 <strong>Conexión de última milla:</strong> De estaciones troncales (Penn Station/Grand Central) a oficinas. Pasajero: si no llevas maletas pesadas, cruzar a pie o en bus M42 es veloz." }
  };

  // 2. Initialize Map
  function initMap() {
    map = L.map('map', {
      center: [40.7350, -73.9500],
      zoom: 11,
      minZoom: 10,
      maxZoom: 16,
      zoomControl: false,
      attributionControl: false
    });

    // Dark Map Layer (Esri Dark Gray - libre, sin marcas de agua)
    L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}', {
      maxZoom: 16
    }).addTo(map);

    // Subtle reference labels
    L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}', {
      maxZoom: 16,
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
        filterLabel.textContent = `${summaryData.clusters[f].icono} ${summaryData.clusters[f].nombre}`;
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
      style: getFeatureStyle,
      onEachFeature: (feature, layer) => {
        layer.on({
          click: () => onZoneSelect(feature, layer),
          touchend: () => onZoneSelect(feature, layer)
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
      const color = cluster ? cluster.color : '#3B82F6';

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
      const color = cluster ? cluster.color : '#3B82F6';
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
      const color = cluster ? cluster.color : '#3B82F6';

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
      storyIcon.textContent = story.icon;
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
        clusterIcon.textContent = cluster.icono;
        clusterName.textContent = `${cluster.nombre} (Habitual)`;
        clusterName.style.color = cluster.color;

        statTrips.textContent = '0';
        statDur.textContent = `${cluster.duracion_min}m`;
        statDist.textContent = `${cluster.distancia_mi}mi`;
        statDominance.textContent = `0%`;

        archetypeDesc.innerHTML = `
          <strong>Sin salidas a las ${timeText.textContent}:</strong> Esta zona no registra viajes en esta hora exacta.<br>
          <em>Su arquetipo habitual para este día es <strong>${cluster.nombre}</strong> (${resumen.total.toLocaleString()} viajes en el mes).</em>
        `;

        updateStreetTip(resumen.dom);
        updateElenaDiagnostics(resumen.dom);
        renderDistribution(resumen.counts, resumen.total);
        return;
      }

      clusterBadge.style.display = 'none';
      if (odsCard) odsCard.style.display = 'none';
      archetypeDesc.innerHTML = `
        <strong>🚕 Zona Atendida por Metro MTA y Apps:</strong> Esta zona no registra viajes de Yellow Cabs en el mes analizado.<br>
        <em>Los taxis amarillos concentran su servicio en Manhattan y aeropuertos (JFK/LGA). En este sector la movilidad se realiza principalmente con <strong>Metro (MTA)</strong> o aplicaciones (Uber/Lyft).</em>
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
    clusterIcon.textContent = cluster.icono;
    clusterName.textContent = cluster.nombre;
    clusterName.style.color = cluster.color;

    statTrips.textContent = info.total.toLocaleString();
    statDur.textContent = `${cluster.duracion_min}m`;
    statDist.textContent = `${cluster.distancia_mi}mi`;
    statDominance.textContent = `${dominancePct}%`;

    const isLow = info.total < 8;
    const notaMuestra = isLow ? `<br><small style="color:#F59E0B">⚠️ Flujo ligero: ${info.total} viajes registrados en esta hora.</small>` : '';

    archetypeDesc.innerHTML = `
      <strong>${cluster.icono} ${cluster.nombre}:</strong> ${cluster.subtitulo}.${notaMuestra}<br>
      ${cluster.desc}
    `;

    updateStreetTip(info.dom);
    updateElenaDiagnostics(info.dom);
    renderDistribution(info.counts, info.total);
  }

  function updateStreetTip(clusterId) {
    if (!fareEstimate || !streetTipText) return;
    if (clusterId === null || clusterId === undefined || !streetAdvice[clusterId]) {
      fareEstimate.textContent = 'Metro $2.90 / App';
      streetTipText.innerHTML = '🚇 <strong>Alternativa de transporte:</strong> Utiliza el metro MTA (24/7) o solicita un auto por app (Uber/Lyft). Los Yellow Cabs rara vez circulan vacíos por este cuadrante.';
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
          <span class="dist-color-box" style="background: ${cMeta.color};"></span>
          <span>${cMeta.icono} ${Math.round(pct)}%</span>
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
    if (btnTourNext) btnTourNext.textContent = (step === 3) ? '¡Empezar a explorar! 🚀' : 'Siguiente →';
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
            <span class="arch-color-badge" style="background: ${c.color};"></span>
            <span class="arch-name">${c.icono} ${c.nombre}</span>
          </div>
          <span class="arch-pct">${c.porcentaje}% (${c.viajes_total.toLocaleString()})</span>
        </div>
        <p class="arch-desc">${c.desc}</p>
        <div class="arch-metrics">
          <span>⏱ ~${c.duracion_min} min</span>
          <span>📍 ~${c.distancia_mi} mi</span>
          <span>🕒 Pico: ~${Math.round(c.hora_pico)}:00 (${c.dia_nombre})</span>
        </div>
        <div style="font-size: 10.5px; color: ${isSelected ? '#38BDF8' : '#6B7280'}; margin-top: 4px; font-weight: 600;">
          ${isSelected ? '✓ Filtrando en el mapa (toca para quitar)' : '🔍 Toca para aislar en el mapa'}
        </div>
      `;

      card.addEventListener('click', () => {
        if (activeFilterCluster === c.id) {
          activeFilterCluster = null;
          activeFilterPill.classList.add('hidden');
        } else {
          activeFilterCluster = c.id;
          filterLabel.textContent = `${c.icono} ${c.nombre}`;
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
