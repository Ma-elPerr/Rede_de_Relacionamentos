import os
import unittest
import sys

# Add project root and 'rede' directory to sys.path for module resolution
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from rede.rede import create_app
from rede import rede_sqlite_cnpj

class TestCamadasRede(unittest.TestCase):

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
                'base_rede': os.path.join(tests_dir, 'test_rede.db'), # Needs a dummy rede.db
                'base_rede_search': '',
                'base_endereco_normalizado': '',
                'base_links': '',
                'base_local': ''
            },
            'ETC': {
                'limite_registros_camada': '1000',
                'tempo_maximo_consulta': '10',
                'ligacao_socio_filial': 'False'
            },
            'API': {'api_keys': ''},
            'INICIO': {'exibe_mensagem_advertencia': 'False'}
        }
        # Create a dummy rede.db for the test
        rede_db_path = os.path.join(tests_dir, 'test_rede.db')
        if not os.path.exists(rede_db_path):
            import sqlite3
            con = sqlite3.connect(rede_db_path)
            con.execute('CREATE TABLE ligacao (id1 TEXT, id2 TEXT, descricao TEXT)')
            con.execute("INSERT INTO ligacao VALUES ('PJ_00000000000001', 'PF_11122233344-SOCIO SANCIONADO', 'socio')")
            con.commit()
            con.close()

        create_app(test_config)

    def test_correcional_feature_in_graph(self):
        """Test if 'correcional' data is correctly added to PF nodes in camadasRede."""
        # We want to expand the company that has the sanctioned partner
        initial_ids = ['PJ_00000000000001']

        # Call the function that builds the graph
        result_json = rede_sqlite_cnpj.camadasRede(listaIds=initial_ids, camada=1)

        # Find the person node in the results
        person_node = None
        for node in result_json.get('no', []):
            if node['id'].startswith('PF_11122233344'):
                person_node = node
                break

        # Assert that the person node was found and has the sanction data
        self.assertIsNotNone(person_node, "Socio (PF) node was not found in the graph.")
        self.assertIn('correcional', person_node, "Node for sanctioned person should have 'correcional' key.")
        self.assertIn('DEMISSAO', person_node['correcional'])
        self.assertIn('Orgao Correcional', person_node['correcional'])

    @classmethod
    def tearDownClass(cls):
        """Clean up dummy files."""
        rede_db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_rede.db')
        if os.path.exists(rede_db_path):
            os.remove(rede_db_path)

if __name__ == '__main__':
    unittest.main()
