import { useState } from 'react';
import {
    Box,
    Autocomplete,
    TextField,
} from '@mui/material';
import { DataForm } from './data-form';

// Componente de formulario de integración
export const IntegrationForm = ({ integrations, onConnectSuccess }) => {
    const [integrationParams, setIntegrationParams] = useState({});
    const [user, setUser] = useState('TestUser');
    const [org, setOrg] = useState('TestOrg');
    const [currType, setCurrType] = useState(null);

    return (
        <Box display="flex" justifyContent="center" alignItems="center" flexDirection="column" sx={{ width: '100%' }}>
            <Box display="flex" flexDirection="column">
                <TextField
                    label="User"
                    value={user}
                    onChange={(e) => setUser(e.target.value)}
                    sx={{ mt: 2 }}
                />
                <TextField
                    label="Organization"
                    value={org}
                    onChange={(e) => setOrg(e.target.value)}
                    sx={{ mt: 2 }}
                />
                <Autocomplete
                    id="integration-type"
                    options={integrations.map((Integration) => Integration.name)}
                    sx={{ width: 300, mt: 2 }}
                    renderInput={(params) => <TextField {...params} label="Integration Type" />}
                    onChange={(e, value) => setCurrType(value)}
                />
            </Box>

            {integrations
                .filter((Integration) => Integration.name === currType)
                .map((IntegrationComponent) => (
                    <IntegrationComponent
                        key={IntegrationComponent.slug}
                        user={user}
                        org={org}
                        setIntegrationParams={setIntegrationParams}
                        onConnectSuccess={onConnectSuccess} // Pasa la prop aquí
                    />
                ))
            }

            {integrationParams?.credentials && (
                <Box sx={{ mt: 2 }}>
                    <DataForm
                        integrationType={currType}
                        credentials={integrationParams?.credentials}
                    />
                </Box>
            )}
        </Box>
    );
};
