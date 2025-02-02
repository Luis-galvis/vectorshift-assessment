import { useState } from 'react';
import { IntegrationForm } from './integration-form';
import { HubspotIntegration } from './integrations/hubspot';
import { AirtableIntegration } from './integrations/airtable';
import { NotionIntegration } from './integrations/notion';

const integrations = [AirtableIntegration, NotionIntegration, HubspotIntegration];

export default function App() {
    const [hubspotData, setHubspotData] = useState([]);

    const handleHubspotData = (contacts) => {
        setHubspotData(contacts);
        console.log('Contactos listos para mostrar:', contacts);
    };

    return (
        <div className="app-container">
            <h1>Integraciones</h1>
            <IntegrationForm 
                integrations={integrations}
                onHubspotConnect={handleHubspotData}
            />
            
            <div className="results-section">
                <h2>Contactos de HubSpot</h2>
                <pre>{JSON.stringify(hubspotData, null, 2)}</pre>
            </div>
        </div>
    );
}
