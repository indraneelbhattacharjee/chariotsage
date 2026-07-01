const chartTitle = document.getElementById('chart-title');
const chartKicker = document.getElementById('chart-kicker');
const chartSignature = document.getElementById('chart-signature');
const chartHighlights = document.getElementById('chart-highlights');
const dashaList = document.getElementById('dasha-list');
const vimshottariList = document.getElementById('vimshottari-list');
const chartForm = document.getElementById('chart-form');
const chartOutput = document.getElementById('chart-output');
const toggleButtons = Array.from(document.querySelectorAll('.toggle-btn'));
const countrySelect = document.getElementById('country');
const stateSelect = document.getElementById('state');
const citySelect = document.getElementById('city');
const manualPlaceField = document.getElementById('manual-place-field');
const manualPlaceInput = document.getElementById('manual-place');
let activeChart = 'lagna';

const PLACES = {
  India: {
    'West Bengal': ['Kolkata', 'Howrah', 'Darjeeling', 'Siliguri'],
    Delhi: ['New Delhi', 'Delhi'],
    Maharashtra: ['Mumbai', 'Pune', 'Nagpur', 'Nashik'],
    Karnataka: ['Bengaluru', 'Mysuru', 'Mangaluru'],
    Telangana: ['Hyderabad', 'Warangal'],
    'Tamil Nadu': ['Chennai', 'Coimbatore', 'Madurai'],
    Kerala: ['Kochi', 'Thiruvananthapuram', 'Kozhikode'],
    Rajasthan: ['Jaipur', 'Jodhpur', 'Udaipur'],
    'Uttar Pradesh': ['Lucknow', 'Varanasi', 'Agra', 'Kanpur'],
    Gujarat: ['Ahmedabad', 'Surat', 'Vadodara'],
    Punjab: ['Amritsar', 'Ludhiana', 'Chandigarh'],
    'Madhya Pradesh': ['Indore', 'Bhopal', 'Gwalior'],
    Other: ['Other']
  },
  'United States': {
    'New York': ['New York City', 'Buffalo', 'Albany'],
    California: ['Los Angeles', 'San Francisco', 'San Diego'],
    Illinois: ['Chicago', 'Springfield'],
    Texas: ['Houston', 'Austin', 'Dallas'],
    Other: ['Other']
  },
  'United Kingdom': {
    England: ['London', 'Manchester', 'Birmingham'],
    Scotland: ['Edinburgh', 'Glasgow'],
    Wales: ['Cardiff'],
    Other: ['Other']
  },
  Canada: {
    Ontario: ['Toronto', 'Ottawa'],
    'British Columbia': ['Vancouver', 'Victoria'],
    Quebec: ['Montreal', 'Quebec City'],
    Other: ['Other']
  },
  Australia: {
    'New South Wales': ['Sydney', 'Newcastle'],
    Victoria: ['Melbourne', 'Geelong'],
    Queensland: ['Brisbane', 'Gold Coast'],
    Other: ['Other']
  },
  'United Arab Emirates': {
    Dubai: ['Dubai'],
    'Abu Dhabi': ['Abu Dhabi'],
    Other: ['Other']
  },
  Singapore: { Singapore: ['Singapore'], Other: ['Other'] },
  Other: { Other: ['Other'] }
};

document.getElementById('year').textContent = new Date().getFullYear();
document.getElementById('dob').max = new Date().toISOString().split('T')[0];

function fillSelect(select, values, selectedValue) {
  select.replaceChildren();
  values.forEach((value) => {
    const option = document.createElement('option');
    option.value = value;
    option.textContent = value;
    option.selected = value === selectedValue;
    select.append(option);
  });
}

function updateStates(preferredState) {
  const states = Object.keys(PLACES[countrySelect.value] || PLACES.Other);
  fillSelect(stateSelect, states, preferredState || states[0]);
  updateCities();
}

function updateCities(preferredCity) {
  const regions = PLACES[countrySelect.value] || PLACES.Other;
  const cities = regions[stateSelect.value] || ['Other'];
  fillSelect(citySelect, cities, preferredCity || cities[0]);
  updateManualPlace();
}

function updateManualPlace() {
  const needsManualPlace = countrySelect.value === 'Other'
    || stateSelect.value === 'Other'
    || citySelect.value === 'Other';
  manualPlaceField.classList.toggle('is-hidden', !needsManualPlace);
  manualPlaceInput.required = needsManualPlace;
}

function selectedPlace() {
  if (manualPlaceInput.required) {
    return manualPlaceInput.value.trim();
  }
  return `${citySelect.value}, ${stateSelect.value}, ${countrySelect.value}`;
}

countrySelect.addEventListener('change', () => updateStates());
stateSelect.addEventListener('change', () => updateCities());
citySelect.addEventListener('change', updateManualPlace);
fillSelect(countrySelect, Object.keys(PLACES), 'India');
updateStates('West Bengal');
updateCities('Kolkata');

function makePlanet(name) {
  const planet = document.createElement('span');
  planet.className = 'planet';
  planet.textContent = name;
  return planet;
}

function renderHouse(house) {
  const houseElement = document.getElementById(`house-${house.house}`);
  if (!houseElement) return;

  houseElement.replaceChildren();
  const number = document.createElement('span');
  number.className = 'house-number';
  number.textContent = house.signNumber || house.house;
  const sign = document.createElement('strong');
  sign.textContent = house.sign;
  const planets = document.createElement('div');
  planets.className = 'planets';
  (house.planets || []).forEach((planet) => planets.append(makePlanet(planet)));
  houseElement.append(number, sign, planets);
}

function renderList(element, items, className) {
  element.replaceChildren();
  items.forEach((item) => {
    const entry = document.createElement(className === 'insight' ? 'li' : 'div');
    entry.textContent = item;
    if (className) entry.className = className;
    element.append(entry);
  });
}

function replayChartAnimation() {
  chartOutput.classList.remove('is-revealing');
  void chartOutput.offsetWidth;
  chartOutput.classList.add('is-revealing');
}

function renderChart(data) {
  chartTitle.textContent = data.type === 'moon' ? 'Moon chart' : 'Lagna chart';
  chartKicker.textContent = `${data.name} • ${data.place}`;
  const anchorSign = data.type === 'moon' ? data.moonSign : data.ascSign;
  chartSignature.textContent = `${data.planet} in ${anchorSign} • ${data.dob} at ${data.tob}`;

  renderList(chartHighlights, data.highlights || [], 'insight');
  (data.houses || []).forEach(renderHouse);
  renderList(dashaList, [
    `Mahadasha — ${data.currentDasha}`,
    `Antardasha — ${data.nextDasha}`,
    `Pratyantar — ${data.subDasha}`
  ], 'dasha-entry');
  renderList(vimshottariList, (data.sequence || []).slice(0, 6), 'dasha-entry');
  replayChartAnimation();
}

async function requestChart(payload) {
  const response = await fetch('/api/chart', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...payload, chartType: activeChart })
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.error || 'The chart could not be calculated. Please check your birth details.');
  }
  return data;
}

function formPayload() {
  const formData = new FormData(chartForm);
  return {
    name: formData.get('name').toString().trim(),
    dob: formData.get('dob').toString(),
    tob: formData.get('tob').toString(),
    pob: selectedPlace()
  };
}

function updateActiveToggle(chartType) {
  activeChart = chartType;
  toggleButtons.forEach((button) => {
    const isActive = button.dataset.chart === chartType;
    button.classList.toggle('active', isActive);
    button.setAttribute('aria-selected', String(isActive));
  });
}

chartForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const submitButton = chartForm.querySelector('button[type="submit"]');
  submitButton.disabled = true;
  submitButton.classList.add('is-loading');
  submitButton.querySelector('span:first-child').textContent = 'Reading the heavens…';
  try {
    renderChart(await requestChart(formPayload()));
    chartOutput.scrollIntoView({ behavior: 'smooth', block: 'center' });
  } catch (error) {
    renderList(chartHighlights, [error.message], 'insight');
  } finally {
    submitButton.disabled = false;
    submitButton.classList.remove('is-loading');
    submitButton.querySelector('span:first-child').textContent = 'Reveal my birth chart';
  }
});

toggleButtons.forEach((button) => {
  button.addEventListener('click', async () => {
    updateActiveToggle(button.dataset.chart);
    if (!chartForm.checkValidity()) return;
    try {
      renderChart(await requestChart(formPayload()));
    } catch (error) {
      renderList(chartHighlights, [error.message], 'insight');
    }
  });
});

updateActiveToggle('lagna');
