import { useState, useEffect } from 'react';
import { Box, Button, CircularProgress } from '@mui/material';
import axios from 'axios';

// Componente de integración
export const NotionIntegration = ({ user, org, setIntegrationParams }) => {
    const [isConnected, setIsConnected] = useState(false);
    const [isConnecting, setIsConnecting] = useState(false);

    const handleConnectClick = async () => {
        try {
            setIsConnecting(true);
            const formData = new FormData();
            formData.append('user_id', user);
            formData.append('org_id', org);
            
            const response = await axios.post(
                'http://localhost:8000/integrations/notion/authorize', 
                formData
            );
            
            const newWindow = window.open(response.data, 'Notion Authorization', 'width=600,height=600');
            
            const pollTimer = setInterval(() => {
                if (newWindow?.closed) {
                    clearInterval(pollTimer);
                    checkNotionCredentials();
                }
            }, 200);
        } catch (e) {
            setIsConnecting(false);
            alert(e.response?.data?.detail || 'Error connecting to Notion');
        }
    };

    const checkNotionCredentials = async () => {
        try {
            const response = await axios.post(
                'http://localhost:8000/integrations/notion/credentials',
                { user_id: user, org_id: org }
            );
            
            if (response.data) {
                setIntegrationParams(prev => ({
                    ...prev,
                    credentials: response.data,
                    type: 'Notion'
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
                    {isConnected ? 'Notion Connected' : 
                     isConnecting ? <CircularProgress size={20} /> : 'Connect to Notion'}
                </Button>
            </Box>
        </Box>
    );
};

// Configuración para el formulario
export const NotionConfig = {
    name: 'Notion',
    slug: 'notion',
    authorizeUrl: '/integrations/notion/authorize'
};