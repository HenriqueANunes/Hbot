import json
import os
from pathlib import Path


DB_PATH = Path(os.getenv('HBOT_DB_PATH', 'hbot_db.json'))


def carregar_db():
    if not DB_PATH.exists():
        return {}

    with DB_PATH.open('r', encoding='utf-8') as arquivo:
        return json.load(arquivo)


def salvar_db(db):
    with DB_PATH.open('w', encoding='utf-8') as arquivo:
        json.dump(db, arquivo, ensure_ascii=False, indent=2)


db = carregar_db()

class Usuario():

    def __init__(self, user=None, cd_servidor=None):
        self.user = user
        self.cd_user = str(user.id)
        self.cd_servidor = str(cd_servidor)
        self.db_user = None

        self.carregar()

    def carregar(self):

        if self.cd_servidor not in db.keys():
            db[self.cd_servidor] = {}

        if self.cd_user not in db[self.cd_servidor].keys():
            db[self.cd_servidor][self.cd_user] = {
                'nome': self.user.name,
                'qtd_mamadas': 0,
                'rpg':{
                    'gold': 0,
                    'pp': 0,
                },
            }

        self.db_user = db[self.cd_servidor][self.cd_user]
        self.db_user.setdefault('rpg', {})
        self.db_user['rpg'].setdefault('gold', 0)
        self.db_user['rpg'].setdefault('pp', 0)
        
        salvar_db(db)

    def add_mamada(self):
        self.db_user['qtd_mamadas'] += 1
        salvar_db(db)

    def get_mamadas(self):
        return self.db_user['qtd_mamadas']

    def get_rank_mamadas(self):
        rank = []
        for _, user in db[self.cd_servidor].items():
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
            salvar_db(db)
            return True, 'Feito!'
        except:
            return False, 'Erro ao setar o gold'

    def add_gold(self, qtd_gold: int=None):
        try:
            self.db_user['rpg']['gold'] += qtd_gold
            salvar_db(db)
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
            salvar_db(db)
            return True, 'Feito!'
        except:
            return False, 'Erro ao settar pp'

    def add_pp(self, qtd_pp: int=None):
        try:
            self.db_user['rpg']['pp'] += qtd_pp
            salvar_db(db)
            return True, '', self.db_user['rpg']['pp']
        except:
            return False, 'Erro ao settar pp', None
            
    def  get_pp(self):
        try:
            return True, '', self.db_user['rpg']['pp']
        except:
            return False, 'Erro ao buscar gold', None 
