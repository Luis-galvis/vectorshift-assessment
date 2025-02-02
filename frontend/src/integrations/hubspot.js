import { useState, useEffect } from 'react';
import { Box, Button, CircularProgress } from '@mui/material';

export const HubspotIntegration = ({ user, org, setIntegrationParams }) => {
    const [isConnected, setIsConnected] = useState(false);
    const [isConnecting, setIsConnecting] = useState(false);

    useEffect(() => {
        const handleMessage = (event) => {
            if (event.data.type === 'hubspot-auth-success') {
                handleAuthSuccess(event.data.user_id, event.data.org_id);
            }
        };

        window.addEventListener('message', handleMessage);
        return () => window.removeEventListener('message', handleMessage);
    }, []);

    const handleConnect = () => {
        setIsConnecting(true);
        const authWindow = window.open(
            `http://localhost:8000/integrations/hubspot/authorize?user_id=${user}&org_id=${org}`,
            'HubSpotAuth',
            'width=600,height=700'
        );

        const checkWindow = setInterval(() => {
            if (authWindow.closed) {
                clearInterval(checkWindow);
                if (!isConnected) setIsConnecting(false);
            }
        }, 500);
    };

    const handleAuthSuccess = async (userId, orgId) => {
        try {
            const response = await fetch(
                `http://localhost:8000/integrations/hubspot/credentials?user_id=${userId}&org_id=${orgId}`
            );
            const credentials = await response.json();
            
            setIntegrationParams({
                credentials: credentials.access_token,
                type: 'HubSpot'
            });
            
            setIsConnected(true);
            loadContacts(userId, orgId);
            
        } catch (error) {
            console.error('Error:', error);
            setIsConnecting(false);
        }
    };

    const loadContacts = async (userId, orgId) => {
        try {
            const response = await fetch(
                `http://localhost:8000/integrations/hubspot/items?user_id=${userId}&org_id=${orgId}`
            );
            const contacts = await response.json();
            console.log('Contactos de HubSpot:', contacts);
        } catch (error) {
            console.error('Error cargando contactos:', error);
        }
    };

    return (
        <Box sx={{ mt: 2 }}>
            <Button
                variant="contained"
                onClick={handleConnect}
                disabled={isConnecting || isConnected}
                color={isConnected ? 'success' : 'primary'}
                startIcon={isConnecting && <CircularProgress size={20} />}
            >
                {isConnected ? 'Conectado ✓' : isConnecting ? 'Conectando...' : 'Conectar HubSpot'}
            </Button>
        </Box>
    );
};

export const HubspotConfig = {
    name: 'HubSpot',
    slug: 'hubspot',
    authorizeUrl: '/integrations/hubspot/authorize'
};