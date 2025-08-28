import os
import unittest
import sys

# Add project root to sys.path for module resolution
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from rede.rede import create_app

class TestApp(unittest.TestCase):

    def setUp(self):
        """Set up a test application instance."""
        tests_dir = os.path.dirname(os.path.abspath(__file__))
        test_config = {
            'BASE': {
                'base_receita': os.path.join(tests_dir, 'test_cnpj.db'),
                'base_rede': '',
                'base_rede_search': '',
                'base_endereco_normalizado': '',
                'base_links': '',
                'base_local': '',
                'referencia_bd': '2024-01'
            },
            'ETC': {
                'limite_registros_camada': '1000',
                'tempo_maximo_consulta': '10',
                'ligacao_socio_filial': 'False',
                'busca_google': 'False',
                'busca_chaves': 'False',
                'geocode_max': '15'
            },
            'API': {'api_keys': ''},
            'INICIO': {'mensagem_advertencia': 'False'}
        }

        self.app = create_app(test_config)
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_main_page(self):
        """Test that the main page loads correctly."""
        response = self.client.get('/rede/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'<title>Rede</title>', response.data)

if __name__ == '__main__':
    unittest.main()
