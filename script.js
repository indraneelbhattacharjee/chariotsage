const chartTitle = document.getElementById('chart-title');
const chartKicker = document.getElementById('chart-kicker');
const chartSignature = document.getElementById('chart-signature');
const chartHighlights = document.getElementById('chart-highlights');
const dashaList = document.getElementById('dasha-list');
const vimshottariList = document.getElementById('vimshottari-list');
const chartForm = document.getElementById('chart-form');
const toggleButtons = Array.from(document.querySelectorAll('.toggle-btn'));
const houseElements = Array.from(document.querySelectorAll('.house'));
let activeChart = 'lagna';

document.getElementById('year').textContent = new Date().getFullYear();

function renderChart(data) {
  chartTitle.textContent = `${data.type === 'moon' ? 'Moon chart' : 'Lagna chart'}`;
  chartKicker.textContent = `${data.name} • ${data.place}`;
  chartSignature.textContent = `${data.planet} in ${data.ascSign} • House ${data.houseNumber} • ${data.dob} • ${data.tob}`;

  chartHighlights.innerHTML = data.highlights.map((item) => `<li>${item}</li>`).join('');

  // Map houses by their house number, not by DOM order
  data.houses.forEach((house) => {
    const houseEl = document.getElementById(`house-${house.house}`);
    if (houseEl) {
      let content = `<span>${house.house}</span><strong>${house.sign}</strong>`;
      
      // Add planets if they exist
      if (house.planets && house.planets.length > 0) {
        content += `<div class="planets">${house.planets.join(' ')}</div>`;
      }
      
      houseEl.innerHTML = content;
      houseEl.classList.toggle('active', house.house === data.houseNumber);
    }
  });

  dashaList.innerHTML = [
    `<div>Mahadasha: ${data.currentDasha}</div>`,
    `<div>Antardasha: ${data.nextDasha}</div>`,
    `<div>Pratyantar: ${data.subDasha}</div>`
  ].join('');

  vimshottariList.innerHTML = data.sequence.slice(0, 6).map((item) => `<div>${item}</div>`).join('');
}

async function requestChart(payload) {
  const response = await fetch('/api/chart', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...payload, chartType: activeChart })
  });
  if (!response.ok) {
    throw new Error('Unable to load chart data');
  }
  return response.json();
}

function updateActiveToggle(chartType) {
  activeChart = chartType;
  toggleButtons.forEach((button) => {
    button.classList.toggle('active', button.dataset.chart === chartType);
  });
}

chartForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const formData = new FormData(chartForm);
  const payload = {
    name: formData.get('name').toString().trim(),
    dob: formData.get('dob').toString(),
    tob: formData.get('tob').toString(),
    pob: formData.get('pob').toString().trim(),
  };
  try {
    const data = await requestChart(payload);
    renderChart(data);
  } catch (error) {
    chartHighlights.innerHTML = `<li>${error.message}</li>`;
  }
});

toggleButtons.forEach((button) => {
  button.addEventListener('click', async () => {
    updateActiveToggle(button.dataset.chart);
    if (chartForm.querySelector('#name').value) {
      const payload = {
        name: chartForm.querySelector('#name').value,
        dob: chartForm.querySelector('#dob').value,
        tob: chartForm.querySelector('#tob').value,
        pob: chartForm.querySelector('#pob').value,
      };
      try {
        const data = await requestChart(payload);
        renderChart(data);
      } catch (error) {
        chartHighlights.innerHTML = `<li>${error.message}</li>`;
      }
    }
  });
});

updateActiveToggle('lagna');
requestChart({
  name: 'Welcome',
  dob: '1990-01-01',
  tob: '12:00',
  pob: 'Kolkata'
}).then(renderChart).catch(() => {
  chartHighlights.innerHTML = '<li>Chart data is currently unavailable.</li>';
});
