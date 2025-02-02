import { useState, useEffect } from 'react';
import { Box, Button, CircularProgress } from '@mui/material';
import axios from 'axios';

// Componente de integración
export const AirtableIntegration = ({ user, org, setIntegrationParams }) => {
    const [isConnected, setIsConnected] = useState(false);
    const [isConnecting, setIsConnecting] = useState(false);

    const handleConnectClick = async () => {
        try {
            setIsConnecting(true);
            const formData = new FormData();
            formData.append('user_id', user);
            formData.append('org_id', org);
            
            const response = await axios.post(
                'http://localhost:8000/integrations/airtable/authorize', 
                formData
            );
            
            const newWindow = window.open(response.data, 'Airtable Authorization', 'width=600,height=600');
            
            const pollTimer = setInterval(() => {
                if (newWindow?.closed) {
                    clearInterval(pollTimer);
                    checkAirtableCredentials();
                }
            }, 200);
        } catch (e) {
            setIsConnecting(false);
            alert(e.response?.data?.detail || 'Error connecting to Airtable');
        }
    };

    const checkAirtableCredentials = async () => {
        try {
            const response = await axios.post(
                'http://localhost:8000/integrations/airtable/credentials',
                { user_id: user, org_id: org }
            );
            
            if (response.data) {
                setIntegrationParams(prev => ({
                    ...prev,
                    credentials: response.data,
                    type: 'Airtable'
                }));
                setIsConnected(true);
            }
        } catch (e) {
            alert(e.response?.data?.detail || 'Error getting credentials');
        }
        setIsConnecting(false);
    };



    return (
        <Box sx={{ mt: 2 }}>
            <Box display="flex" alignItems="center" justifyContent="center" sx={{ mt: 2 }}>
                <Button
                    variant="contained"
                    onClick={handleConnectClick}
                    color={isConnected ? 'success' : 'primary'}
                    disabled={isConnecting || isConnected}
                >
                    {isConnected ? 'Airtable Connected' : 
                     isConnecting ? <CircularProgress size={20} /> : 'Connect to Airtable'}
                </Button>
            </Box>
        </Box>
    );
};

// Configuración para el formulario
export const AirtableConfig = {
    name: 'Airtable',
    slug: 'airtable',
    authorizeUrl: '/integrations/airtable/authorize'
};
