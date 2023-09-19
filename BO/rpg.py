import random
import re


class Rpg():
    
    # ([1-\100]*d[0-\100]+)\s?\+?\s?([1-\100]*d[1-\100]+)?
    def get_dados(self, regex=None):
        regex = re.search("(?P<dado1>[\d]*d[\d]+)\ ?(?P<operador>\+?\-?\*?\/?)\ ?(?P<dado2>[\d]*d[\d]+)?", regex)
        
        response = ''
        if regex:
            dict_regex = regex.groupdict()
            qtd_dado1, numero1 = dict_regex.get('dado1').split('d')
    
            operador = dict_regex.get('operador')

            soma1, lista1 = self.roll_brabo(qtd_dados=qtd_dado1, numero=numero1)

            if dict_regex.get('dado2') and operador:
                qtd_dado2, numero2 = dict_regex.get('dado2').split('d')
                
                soma2, lista2 = self.roll_brabo(qtd_dados=qtd_dado2, numero=numero2)
                soma_total = eval(str(soma1) + operador + str(soma2))

                response = str(soma_total) + ' <- ' + str(lista1) + ' ' + dict_regex.get('dado1') + ' ' + operador + ' ' + str(lista2) + ' ' + dict_regex.get('dado2')

            else:
                response = str(soma1) + ' <- ' + str(lista1) + ' ' + dict_regex.get('dado1')

            return response
            

    def roll_brabo(self, qtd_dados=None, numero=None):
        lista_dados = []
        if qtd_dados:
            qtd_dados = int(qtd_dados)
        else:
            qtd_dados = 1
        
        for d in range(0, qtd_dados):
            lista_dados.append(random.randint(1, int(numero)))

        soma = 0
        for dado in lista_dados:
            soma += dado


        return soma, lista_dados
