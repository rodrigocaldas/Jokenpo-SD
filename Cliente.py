#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Cliente
"""

# importações necessárias
from socket import socket, gethostname, gethostbyname, AF_INET, SOCK_STREAM
from pickle import dumps, loads
from thread import start_new_thread

# configurações do cliente
SERVER_TCP_IP = '177.105.51.165'
SERVER_TCP_PORT = 5000
# se a máquina cliente também estiver executando o servidor, definir o IP manualmente
TCP_IP = gethostbyname(gethostname())
client_socket = socket(AF_INET, SOCK_STREAM)
client_socket.connect((SERVER_TCP_IP, SERVER_TCP_PORT))

# configurações de peer to peer
LISTENING_TCP_PORT = 5001
GAME_TCP_PORT = 5002
listening_socket = socket(AF_INET, SOCK_STREAM)
listening_socket.bind(('0.0.0.0', LISTENING_TCP_PORT))
listening_socket.listen(1)
game_socket = socket(AF_INET, SOCK_STREAM)
playing = False
usuarios_conectados = set()

def menu():
    """
        Exibe o menu e retorna a opção selecionada.
    """
    print 'Opções:\n\t(1) Entrar\n\t(2) Cadastrar\n\t(3) Sair'
    return raw_input('Digite a opção desejada: ')


def login(nome_usuario, senha):
    """
        Realiza a tentativa de login do usuário e caso bem-sucedido retorna o
        conjunto de usuários conectados. Caso contrário apenas retorna um conjunto
        vazio, indicando que o usuário não tem acesso aos conectados, ou seja,
        não foi possível efetuar login.
    """
    client_socket.send( dumps(('1', nome_usuario, senha, TCP_IP)) )
    return loads(client_socket.recv(1024))


def cadastrar(nome_usuario, senha):
    """
        Realiza a tentativa de cadastro do usuário e retorna False se houver erros.
    """
    client_socket.send( dumps(('2', nome_usuario, senha)) )
    return loads(client_socket.recv(1024))


def listar_usuarios_conectados(nome_usuario):
    """
        Lista o conjunto de usuários conectados, excluindo o usuário logado.
    """
    print 'Lista de usuários conectados:'
    if len(usuarios_conectados) < 2:
        print '\tNão há outros usuários online!'

    for usuario, pontos, ip in usuarios_conectados:
        if usuario != nome_usuario:
            print '\tUsuário: {usuario}, {pontos} pontos'.format(
                usuario=usuario,
                pontos=pontos
            )


def atualizar_usuarios_conectados(nome_usuario):
    """
        Atualiza na tela o conjunto usuários conectados
    """
    global usuarios_conectados
    while True:
        usuarios_conectados = loads(client_socket.recv(1024))
        listar_usuarios_conectados(nome_usuario)
        print 'Se você desja desafiar um jogador, digite o nome do adversário.'
        print 'Se você deseja sair pressione ctrl+c.'


def buscar_ip_adversario(adversario):
    """
        Retorna o ip do adversario caso encontrado, senão retorna vazio.
    """
    for usuario in usuarios_conectados:
        if usuario[0] == adversario:
            return usuario[2]

    return ''


def partida(nome_usuario, conn=None):
    """
        Realiza o controle de partida.
    """
    global playing
    global game_socket
    # começa o jogo e realiza a jogada
    playing = True
    jogada = raw_input('Digite sua jogada (pedra, papel, ou tesoura): ')
    while not jogada in ('pedra', 'papel', 'tesoura'):
        jogada = raw_input('Jogada inválida. Digite sua jogada novamente (pedra, papel, ou tesoura): ')

    # envia a jogada para o adversário e recebe jogada dele de volta
    if conn:
        jogada_adversario = conn.recv(1024)
        conn.send(jogada)
    else:
        game_socket.send(jogada)
        jogada_adversario = game_socket.recv(1024)

    # resultado da partida
    if jogada == 'papel' and jogada_adversario == 'pedra':
        print '\nVocê ganhou!\n'
        client_socket.send( dumps((nome_usuario, 1)) )
    elif jogada == 'pedra' and jogada_adversario == 'tesoura':
        print '\nVocê ganhou!\n'
        client_socket.send( dumps((nome_usuario, 1)) )
    elif jogada == 'tesoura' and jogada_adversario == 'papel':
        print '\nVocê ganhou!\n'
        client_socket.send( dumps((nome_usuario, 1)) )
    elif jogada == 'papel' and jogada_adversario == 'tesoura':
        print '\nVocê perdeu!\n'
    elif jogada == 'pedra' and jogada_adversario == 'papel':
        print '\nVocê perdeu!\n'
    elif jogada == 'tesoura' and jogada_adversario == 'pedra':
        print '\nVocê perdeu!\n'
    else:
        print '\nVocê empatou!\n'

    # termina o jogo e reinicia o socket para liberá-lo para outras partidas
    playing = False
    game_socket.close()
    game_socket = socket(AF_INET, SOCK_STREAM)


def desafiar_jogador(nome_usuario):
    """
        Realiza o desafio a outro jogador e então é iniciada uma partida melhor de três.
    """
    global game_socket
    while True:
        adversario = raw_input(
            'Se você desja desafiar um jogador, digite o nome do adversário.\n'\
            'Se você deseja sair pressione ctrl+c.\n'
        )
        if adversario:
            # se houver adversário, então o jogador realizou um desafio
            ip_adversario = buscar_ip_adversario(adversario)
            while not ip_adversario:
                adversario = raw_input(
                    'Jogador não encontrado, digite novamente o nome do adversário.\n'
                )
                if not adversario:
                    # se não houver adversário, então o jogador foi desafiado
                    partida(nome_usuario)
                    break
                ip_adversario = buscar_ip_adversario(adversario)

            if not adversario:
                # se não houver adversário, então o jogador saiu de um desafio
                continue

            # desafia o adversário
            game_socket.connect((ip_adversario, LISTENING_TCP_PORT))
            game_socket.send(TCP_IP)
            adversario_disponivel = game_socket.recv(1024)
            if adversario_disponivel:
                # se o adversário está disponível, reconecta o socket de jogo como
                # servidor e inicia a partida
                game_socket.close()
                game_socket = socket(AF_INET, SOCK_STREAM)
                game_socket.bind(('0.0.0.0', GAME_TCP_PORT))
                game_socket.listen(1)
                conn, addr = game_socket.accept()
                partida(nome_usuario, conn)
                conn.close()
            else:
                print 'Este jogador está ocupado, espere a partida acabar ou desafie outro.'
        else:
            # se não houver adversário, então o jogador foi desafiado
            partida(nome_usuario)


def receber_desafio():
    """
        O jogador foi desafiado e uma partida melhor de três é iniciada.
    """
    global game_socket
    while True:
        conn, addr = listening_socket.accept()
        ip_desafiante = conn.recv(1024)
        if not playing:
            # se não está jogando, então reinicia o socket de jogo e aceita o desafio
            conn.send(dumps(True))
            game_socket.close()
            game_socket = socket(AF_INET, SOCK_STREAM)
            game_socket.connect((ip_desafiante, GAME_TCP_PORT))
            print 'Você foi desafiado. Aperte ENTER para jogar.'
        else:
            # se estiver jogando, então recusa o desafio
            conn.send(dumps(False))


def main():
    opcao = 'inicio'
    while not opcao in ('1', '2', '3'):
        opcao = menu()
        if opcao == '1':
            # login de usuário
            nome_usuario = raw_input('Digite o seu nome de usuário: ')
            senha = raw_input('Digite a sua senha: ')
            usuarios_conectados = login(nome_usuario, senha)
            if not usuarios_conectados:
                # caso o login falhe, é exibida uma mensagem de erro
                print 'Nome de usuário e/ou senha incorretos!'
                opcao = 'erro'

        elif opcao == '2':
            # cadastro de usuário
            nome_usuario = raw_input('Digite o seu nome de usuário: ')
            senha = raw_input('Digite a sua senha: ')
            sucesso = cadastrar(nome_usuario, senha)
            if sucesso:
                # ao realizar o cadastro, o login e efetuado automaticamente
                print 'Cadastro realizado com sucesso!'
                usuarios_conectados = login(nome_usuario, senha)
            else:
                # em caso de erro, é exibida uma mensagem
                print 'Erro ao cadastrar. Para corrigir vefique as'\
                       ' possibilidades abaixo e tente novamente.\n'\
                       '\t- Campo de usuário e/ou senha em branco;\n'\
                       '\t- Nome de usuário já cadastrado.'
                opcao = 'erro'

        elif opcao == '3':
            print 'Tchau!'

        else:
            print 'Opção inválida!'


    if opcao != '3':
        try:
            listar_usuarios_conectados(nome_usuario)
            start_new_thread(atualizar_usuarios_conectados, (nome_usuario,))
            start_new_thread(desafiar_jogador, (nome_usuario,))
            start_new_thread(receber_desafio, ())
            while True:
                pass
        except (KeyboardInterrupt, SystemExit):
            # após sair do jogo
            client_socket.send( dumps((nome_usuario,)) )


    client_socket.close()
    return 0

if __name__ == '__main__':
    main()
