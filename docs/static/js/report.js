// Report Tab Logic
if (reportTabBtn) {
    reportTabBtn.addEventListener('click', () => {
        loadReport();
    });
}

function loadReport() {
    reportContentDiv.innerHTML = '<p>Loading report data...</p>';

    fetch('/api/report')
        .then(res => res.json())
        .then(data => {
            if (data.status === 'No data') {
                reportContentDiv.innerHTML = `
                    <h3>Simulation Report</h3>
                    <p>No simulation data available. Please run a simulation first in the "Calculation" tab.</p>
                `;
                return;
            }

            renderReport(data);
        })
        .catch(err => {
            console.error(err);
            reportContentDiv.innerHTML = `<p style="color:red">Error loading report: ${err}</p>`;
        });
}

function renderReport(data) {
    const summary = data.summary;
    const topZones = data.top_congested_zones;

    let html = `<h3>Simulation Report</h3>`;

    html += `
        <h4>Summary</h4>
        <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
            <tr>
                <td style="border: 1px solid #ddd; padding: 8px;">Total Zones</td>
                <td style="border: 1px solid #ddd; padding: 8px;">${summary.total_zones.toLocaleString()}</td>
            </tr>
            <tr>
                <td style="border: 1px solid #ddd; padding: 8px;">Active Traffic Zones</td>
                <td style="border: 1px solid #ddd; padding: 8px;">${summary.active_traffic_zones.toLocaleString()}</td>
            </tr>
            <tr>
                <td style="border: 1px solid #ddd; padding: 8px;">Total Network Flow (Vol)</td>
                <td style="border: 1px solid #ddd; padding: 8px;">${summary.total_network_flow.toLocaleString()}</td>
            </tr>
        </table>
    `;

    html += `<h4>Top 5 Congested Zones</h4>`;
    if (topZones && topZones.length > 0) {
        html += `
            <table style="width: 100%; border-collapse: collapse;">
                <thead style="background-color: #f2f2f2;">
                    <tr>
                        <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Zone ID</th>
                        <th style="border: 1px solid #ddd; padding: 8px; text-align: right;">Total Flow</th>
                    </tr>
                </thead>
                <tbody>
        `;

        topZones.forEach(z => {
            html += `
                <tr>
                    <td style="border: 1px solid #ddd; padding: 8px;">${z.key_code}</td>
                    <td style="border: 1px solid #ddd; padding: 8px; text-align: right;">${z.total_flow.toLocaleString()}</td>
                </tr>
            `;
        });

        html += `</tbody></table>`;
    } else {
        html += `<p>No traffic data found.</p>`;
    }

    if (data.city_model) {
        const cm = data.city_model;
        html += `
            <hr style="margin: 20px 0;">
            <h3>City Dynamics Report</h3>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="border: 1px solid #ddd; padding: 8px;">Max Land Price</td>
                    <td style="border: 1px solid #ddd; padding: 8px;">${cm.max_land_price.toFixed(2)}</td>
                </tr>
                <tr>
                    <td style="border: 1px solid #ddd; padding: 8px;">Max Pop/Cell</td>
                    <td style="border: 1px solid #ddd; padding: 8px;">${cm.max_population_cell.toFixed(0)}</td>
                </tr>
                <tr>
                    <td style="border: 1px solid #ddd; padding: 8px;">Total Population (Simulated Range)</td>
                    <td style="border: 1px solid #ddd; padding: 8px;">${cm.total_population.toLocaleString()}</td>
                </tr>
            </table>
        `;
    }

    html += `
        <div style="margin-top: 20px;">
            <button onclick="alert('CSV Export feature coming soon!')" style="padding: 10px; cursor: pointer;">Download CSV</button>
        </div>
    `;

    reportContentDiv.innerHTML = html;
}
