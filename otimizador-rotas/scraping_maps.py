from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
import webbrowser

from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

from time import sleep
import pulp
import itertools

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service)
driver.get("https://www.google.com.br/maps")
sleep(5)
def esta_na_aba_de_rotas():
    xpath = '//button[@aria-label="Fechar rotas"]'
    botao_rotas = driver.find_elements(By.XPATH, xpath)
    return len(botao_rotas) > 0

def busca_endereco(endereco, num_caixa=1):
    if not esta_na_aba_de_rotas():
        print("Não está na aba de rotas. Buscando endereço na barra de pesquisa.")
        busca_vazia = driver.find_element(By.ID, 'searchboxinput')
        busca_vazia.clear()
        sleep(2)
        busca_vazia.send_keys(endereco)
        sleep(2)
        busca_vazia.send_keys(Keys.RETURN)
        sleep(2)
    else:
        print(f"Está na aba de rotas. Tentando buscar endereço na caixa {num_caixa}.")
        caixas = driver.find_elements(By.XPATH, '//div[contains(@id, "directions-searchbox")]//input')
        caixas = [c for c in caixas if c.is_displayed()]
        if len(caixas) >= num_caixa:
            caixa_endereco = caixas[num_caixa - 1]
            caixa_endereco.send_keys(Keys.CONTROL + 'a')
            caixa_endereco.send_keys(Keys.DELETE)
            caixa_endereco.send_keys(endereco)
            caixa_endereco.send_keys(Keys.RETURN)
        else:
            print(f"Não conseguimos adicionar o endereço. Caixas disponíveis: {len(caixas)}, Caixa solicitada: {num_caixa}")

def define_rota(driver):
    wait = WebDriverWait(driver, timeout=10)

    try:
        # Espera o botão aparecer e ser clicável
        rota = wait.until(EC.element_to_be_clickable(
            (By.XPATH, '//*[@id="QA0Szd"]/div/div/div[1]/div[2]/div/div[1]/div/div/div[4]/div[1]/button')
        ))
        rota.click()
        print("Botão de rota clicado com sucesso!")

        sleep(3)  # Aguarda a interface responder
        
        # Espera o botão de "Fechar rotas" aparecer
        xpath = '//button[@aria-label="Fechar rotas"]'
        botao_rotas = wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
        print("Botão de fechar rotas encontrado!")

    except Exception as e:
        print(f"Erro ao definir rota: {e}")


def seleciona_tipo_conducao():
    xpath = '//*[@id="omnibox-directions"]/div/div[2]/div/div/div/div[2]/button/div[1]'
    wait = WebDriverWait(driver, timeout=3)

    try:
        print("Tentando localizar o botão de tipo de condução...")
        botao_conducao = wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
        print("Botão de tipo de condução localizado, tentando clicar...")
        botao_conducao.click()
        print("Tipo de condução selecionado com sucesso!")
    except Exception as e:
        print(f"Erro ao selecionar tipo de condução: {e}")


def adiciona_caixa_destino():
    xpath = '//*[@id="omnibox-directions"]/div/div[3]/button'
    wait = WebDriverWait(driver, timeout=2)

    try:
        print("Tentando localizar o botão de adicionar destino...")
        adiciona_destino = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
        print("Botão localizado, tentando clicar...")
        adiciona_destino.click()
        print("Caixa de destino adicionada com sucesso!")
    except Exception as e:
        print(f"Erro ao adicionar caixa de destino: {e}")

def retorna_tempo_total():
    xpath = '//div[@id="section-directions-trip-0"]//div[contains(text(),"min")]'
    wait = WebDriverWait(driver,timeout=3)
    elemento_tempo = wait.until(EC.presence_of_element_located((By.XPATH,xpath)))
    return int(elemento_tempo.text.replace(' min',''))

def retorna_km_total():
    xpath = '//div[@id="section-directions-trip-0"]//div[contains(text(),"km")]'
    wait = WebDriverWait(driver,timeout=3)
    elemento_tempo = wait.until(EC.presence_of_element_located((By.XPATH,xpath)))
    return float(elemento_tempo.text.replace(' km','').replace(',','.'))


#===================

def gera_pares_distancia(enderecos):
    distancia_pares = {}
    driver.get("https://www.google.com/maps")
    busca_endereco(enderecos[0], 1)
    define_rota(driver)
    seleciona_tipo_conducao()

    for i, end1 in enumerate(enderecos):
        sleep(1)
        busca_endereco(end1, 1)
        sleep(1)
        for j, end2 in enumerate(enderecos):
            if i != j:
                sleep(1)
                busca_endereco(end2, 2)
                sleep(1)
                tempo_par = retorna_tempo_total()
                distancia_pares[f'{i}_{j}'] = tempo_par
    
    return distancia_pares
   

def gera_otimizacao(enderecos, distancia_pares):

    def distancia(end1, end2):
        return distancia_pares[f'{end1}_{end2}']
    
    prob = pulp.LpProblem('TSP', pulp.LpMinimize)

    x = pulp.LpVariable.dicts('x', [(i, j) for i in range(len(enderecos)) for j in range(len(enderecos)) if i != j], cat='Binary')

    prob += pulp.lpSum([distancia(i, j) * x[(i, j)] for i in range(len(enderecos)) for j in range(len(enderecos)) if i != j])

    for i in range(len(enderecos)):
        prob += pulp.lpSum([x[(i, j)] for j in range(len(enderecos)) if i != j]) == 1
        prob += pulp.lpSum([x[(j, i)] for j in range(len(enderecos)) if i != j]) == 1
 
    for k in range(len(enderecos)):
        for S in range(2, len(enderecos)):
            for subset in itertools.combinations([i for i in range(len(enderecos)) if i != k], S):
                prob += pulp.lpSum([x[(i, j)] for i in subset for j in subset if i != j]) <= len(subset) - 1
    
    prob.solve(pulp.PULP_CBC_CMD())

    solucao = []
    cidade_inicial = 0
    proxima_cidade = cidade_inicial
    while True:
        for j in range(len(enderecos)):
            if j != proxima_cidade and x[(proxima_cidade, j)].value() == 1:
               solucao.append((proxima_cidade, j))
               proxima_cidade = j
               break
        if proxima_cidade == cidade_inicial:
            break
    
    print('Rota:')
    for i in range(len(solucao)):
        print(solucao[i][0], ' ->> ', solucao[i][1])
    
    return solucao


def mostra_rota_otimizada(enderecos, rota):
    driver.get("https://www.google.com/maps")

    print("Buscando o primeiro endereço...")
    busca_endereco(enderecos[0], 1)
    define_rota(driver)

    for i in range(len(rota)):
        print(f"Adicionando destino para a rota {i}")
        busca_endereco(enderecos[rota[i][0]], i + 1)
        sleep(5)  # Aguarde antes de adicionar a caixa de destino
        print("Antes de adicionar caixa de destino")
        adiciona_caixa_destino()
        print("Depois de adicionar caixa de destino")
    
    print("Buscando o endereço final...")
    busca_endereco(enderecos[0], len(enderecos) + 1)

    # Mensagem final de depuração
    print("Rota encontrada!")
    sleep(10)  # Aguarde 10 segundos antes de fechar o programa
    driver.quit()  # Fecha o navegador
    

if __name__ == "__main__":
    enderecos = [
                "ST Setor Terminal Norte, Lote J, S/N - Asa Norte, Brasília - DF, 70770-916", 
                "St Setor Terminal Norte, Lote J, S/N Asa Norte 512/513 - Asa Norte, Brasília - DF, 70297-400",  
                "Asa Norte Entrequadra Norte 504/505 Bloco A - Asa Norte, Brasília - DF, 70760-545", 
                "Shc/sul Eq, 402/403 - Asa Sul, Brasília - DF, 70236-400", 
                "Shc/sul EQ, 310 BL A - Asa Sul, Brasília - DF, 70364-400",
    ]


    distancia_pares = gera_pares_distancia(enderecos)
    rota_correta = gera_otimizacao(enderecos,distancia_pares)

    mostra_rota_otimizada(enderecos,rota_correta)
    
    sleep(600)




