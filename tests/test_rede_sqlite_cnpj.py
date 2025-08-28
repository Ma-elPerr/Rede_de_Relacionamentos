import os
import sys
import unittest

# Add project root to sys.path for module resolution
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from rede.rede import create_app
from rede import rede_sqlite_cnpj

class TestJsonDadosReceita(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """
        Set up the test environment by creating a test app instance.
        This initializes all the modules with the test configuration.
        """
        tests_dir = os.path.dirname(os.path.abspath(__file__))
        test_config = {
            'BASE': {
                'base_receita': os.path.join(tests_dir, 'test_cnpj.db'),
                'base_rede': '',
                'base_local': ''
            },
            'ETC': {},
            'API': {},
            'INICIO': {}
        }
        # Creating the app with test_config initializes the modules
        create_app(test_config)

    def test_sancao_data_retrieval(self):
        """Test if CNEP and CEIS data is correctly retrieved by jsonDadosReceita."""
        test_cnpjs = ['00000000000001', '11111111000111', '22222222000122']

        results_list = rede_sqlite_cnpj.jsonDadosReceita(test_cnpjs)

        results = {n['id']: n for n in results_list}

        self.assertIn('PJ_00000000000001', results)
        self.assertNotIn('cnep', results['PJ_00000000000001'])
        self.assertNotIn('ceis', results['PJ_00000000000001'])

        self.assertIn('PJ_11111111000111', results)
        cnep_data = results['PJ_11111111000111'].get('cnep')
        self.assertIsNotNone(cnep_data)
        self.assertIn('Suspensão', cnep_data)
        self.assertIn('Orgao CNEP', cnep_data)
        self.assertNotIn('ceis', results['PJ_11111111000111'])

        self.assertIn('PJ_22222222000122', results)
        ceis_data = results['PJ_22222222000122'].get('ceis')
        self.assertIsNotNone(ceis_data)
        self.assertIn('Multa', ceis_data)
        self.assertIn('Orgao CEIS', ceis_data)
        self.assertNotIn('cnep', results['PJ_22222222000122'])

if __name__ == '__main__':
    unittest.main()
