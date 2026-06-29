import os
from pathlib import Path

from tinydb import Query, TinyDB

DB_PATH = Path(os.getenv('HBOT_DB_PATH', 'hbot_db.json'))
USER_TABLE_NAME = 'usuarios'
"""
Estrutura do banco (TinyDB):

- Arquivo: `hbot_db.json` (ou valor de `HBOT_DB_PATH`)
- Tabela: `usuarios`
- Cada documento da tabela:
  {
    "cd_servidor": "<id do servidor Discord em string>",
    "cd_user": "<id do usuário Discord em string>",
    "nome": "<nome do usuário>",
    "qtd_mamadas": <int>,
    "rpg": {
      "gold": <int>,
      "pp": <int>
    }
  }
"""


db = TinyDB(DB_PATH, ensure_ascii=False, indent=2)
usuarios_table = db.table(USER_TABLE_NAME)
usuario_query = Query()


class Usuario():

    def __init__(self, user=None, cd_servidor=None):
        self.user = user
        self.cd_user = str(user.id)
        self.cd_servidor = str(cd_servidor)
        self.db_user = None
        self.doc_id = None

        self.carregar()

    def _buscar_usuario_doc(self):
        return usuarios_table.get(
            (usuario_query.cd_servidor == self.cd_servidor)
            & (usuario_query.cd_user == self.cd_user)
        )

    def _salvar_usuario(self):
        usuarios_table.update(self.db_user, doc_ids=[self.doc_id])

    def carregar(self):
        doc = self._buscar_usuario_doc()
        if not doc:
            self.doc_id = usuarios_table.insert({
                'cd_servidor': self.cd_servidor,
                'cd_user': self.cd_user,
                'nome': self.user.name,
                'qtd_mamadas': 0,
                'rpg': {
                    'gold': 0,
                    'pp': 0,
                },
            })
            doc = usuarios_table.get(doc_id=self.doc_id)

        self.doc_id = doc.doc_id
        self.db_user = dict(doc)
        self.db_user.setdefault('rpg', {})
        self.db_user['rpg'].setdefault('gold', 0)
        self.db_user['rpg'].setdefault('pp', 0)
        
        self._salvar_usuario()

    def add_mamada(self):
        self.db_user['qtd_mamadas'] += 1
        self._salvar_usuario()

    def get_mamadas(self):
        return self.db_user['qtd_mamadas']

    def get_rank_mamadas(self):
        rank = []
        users = usuarios_table.search(usuario_query.cd_servidor == self.cd_servidor)
        for user in users:
            rank.append(dict(user))
        rank.sort(reverse=True, key=lambda user: user['qtd_mamadas'])
        
        # resposta = '\n'.join([f"{index}: {user['nome']} mamou {user['qtd_mamadas']} vezes" for index,user in enumerate(rank, start=1)])


        posicao = 0
        qtd_anterior = 0
        response = ''
        
        for user in rank:
            if qtd_anterior != user['qtd_mamadas']:
                posicao += 1
                
            response += f"{posicao}: {user['nome']} mamou {user['qtd_mamadas']} vezes\n"
            
            qtd_anterior = user['qtd_mamadas']

        
        return response

    def set_gold(self, qtd_gold: int=None):
        try:
            if not qtd_gold:
                return False, 'É necessário dizer a quantidade de gold'
                
            self.db_user['rpg']['gold'] = qtd_gold
            self._salvar_usuario()
            return True, 'Feito!'
        except:
            return False, 'Erro ao setar o gold'

    def add_gold(self, qtd_gold: int=None):
        try:
            self.db_user['rpg']['gold'] += qtd_gold
            self._salvar_usuario()
            return True, '', self.db_user['rpg']['gold']
        except:
            return False, 'Erro ao adicionar valor', None

    def  get_gold(self):
        try:
            return True, '', self.db_user['rpg']['gold']
        except:
            return False, 'Erro ao buscar gold', None

    def set_pp(self, qtd_pp: int=None):
        try:
            if not qtd_pp:
                return False, 'É necessário dizer a quantidade de pp'
                
            self.db_user['rpg']['pp'] = qtd_pp
            self._salvar_usuario()
            return True, 'Feito!'
        except:
            return False, 'Erro ao settar pp'

    def add_pp(self, qtd_pp: int=None):
        try:
            self.db_user['rpg']['pp'] += qtd_pp
            self._salvar_usuario()
            return True, '', self.db_user['rpg']['pp']
        except:
            return False, 'Erro ao settar pp', None
            
    def  get_pp(self):
        try:
            return True, '', self.db_user['rpg']['pp']
        except:
            return False, 'Erro ao buscar gold', None 
