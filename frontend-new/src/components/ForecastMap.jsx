import React, { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap, Circle } from 'react-leaflet';

// Component to bundle map updates
function ChangeView({ center }) {
    const map = useMap();
    map.setView(center, map.getZoom());
    return null;
}

const ForecastMap = ({ lat, lon, property = 'T2M' }) => {
    const [gridData, setGridData] = useState([]);

    // Leaflet needs to know the container height
    const position = [lat || 51.505, lon || -0.09];

    // Map property code to Open-Meteo param
    const getParam = (p) => {
        switch (p) {
            case 'T2M': return 'temperature_2m';
            case 'RH2M': return 'relative_humidity_2m';
            case 'WS2M': return 'wind_speed_10m';
            default: return 'temperature_2m';
        }
    };

    useEffect(() => {
        if (!lat || !lon) return;

        const fetchGridData = async () => {
            // Generate 5x5 grid points
            const lats = [];
            const lons = [];
            const offsets = [-0.2, -0.1, 0, 0.1, 0.2]; // 5 steps

            offsets.forEach(latOffset => {
                offsets.forEach(lonOffset => {
                    lats.push(lat + latOffset);
                    lons.push(lon + lonOffset);
                });
            });

            const param = getParam(property);
            // Batch fetch from Open-Meteo
            const url = `https://api.open-meteo.com/v1/forecast?latitude=${lats.join(',')}&longitude=${lons.join(',')}&current=${param}`;

            try {
                const res = await fetch(url);
                const data = await res.json();

                if (Array.isArray(data)) {
                    const newGrid = data.map((pointData, i) => ({
                        lat: lats[i],
                        lon: lons[i],
                        val: pointData.current[param]
                    }));
                    setGridData(newGrid);
                }
            } catch (err) {
                console.error("Failed to fetch map grid", err);
            }
        };

        fetchGridData();
    }, [lat, lon, property]);

    const getColor = (val) => {
        if (property === 'T2M') {
            if (val < 10) return '#3b82f6'; // Blue
            if (val < 20) return '#10b981'; // Green
            if (val < 30) return '#f59e0b'; // Yellow/Orange
            return '#ef4444'; // Red
        }
        if (property === 'RH2M') {
            // Humidity: 0-100
            if (val < 30) return '#ef4444'; // Red (Dry)
            if (val < 60) return '#f59e0b'; // Yellow
            if (val < 80) return '#10b981'; // Green (Comfortable)
            return '#3b82f6'; // Blue (Humid)
        }
        if (property === 'WS2M') {
            // Wind: 0-100+ km/h
            if (val < 10) return '#10b981'; // Green (Calm)
            if (val < 25) return '#f59e0b'; // Yellow (Breezy)
            if (val < 50) return '#ef4444'; // Red (High Wind)
            return '#7f1d1d'; // Dark Red (Storm)
        }
        return '#3b82f6';
    };

    return (
        <MapContainer center={position} zoom={10} scrollWheelZoom={false} className="h-full w-full rounded-xl z-0">
            <ChangeView center={position} />
            <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            {lat && lon && (
                <Marker position={position}>
                    <Popup>
                        Selected Location <br /> {lat.toFixed(2)}, {lon.toFixed(2)}
                    </Popup>
                </Marker>
            )}

            {/* Heatmap Grid */}
            {gridData.map((pt, i) => (
                <Circle
                    key={i}
                    center={[pt.lat, pt.lon]}
                    pathOptions={{
                        fillColor: getColor(pt.val),
                        color: getColor(pt.val),
                        fillOpacity: 0.4,
                        opacity: 0.6
                    }}
                    radius={5000} // 5km radius
                >
                    <Popup>
                        {property}: {pt.val}
                    </Popup>
                </Circle>
            ))}
        </MapContainer>
    );
};

export default ForecastMap;
