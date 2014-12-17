#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Servidor
"""

# importações necessárias
from socket import socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR
from select import select
from pickle import dumps, loads
from dal import DAL, Field

# configurações do servidor
TCP_IP = '0.0.0.0'
TCP_PORT = 5000
server_socket = socket(AF_INET, SOCK_STREAM)
server_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
server_socket.bind((TCP_IP, TCP_PORT))
server_socket.listen(10)
CONNECTION_LIST = [server_socket]

# criando conexão com o banco de dados
db = DAL('sqlite://storage.sqlite')

# definindo tabela de usuário
table_usuarios = db.define_table(
    'usuarios',
    Field('nome_usuario', notnull=True, unique=True),
    Field('senha', notnull=True),
    Field('pontos', 'integer', default=0)
)

# lista de usuários conectados
usuarios_conectados = set()


def login(nome_usuario, senha, ip_usuario):
    """
        Realiza a tentativa de login do usuário e caso bem-sucedido o adiciona
        no conjunto de usuários conectados e retorna True. Caso contrário apenas
        retorna False.
    """
    usuario = db(table_usuarios.nome_usuario == nome_usuario).select().first()
    if usuario and usuario.senha == senha:
        usuarios_conectados.add((usuario.nome_usuario, usuario.pontos, ip_usuario))
        return True

    return False


def cadastrar(nome_usuario, senha):
    """
        Realiza a tentativa de cadastro do usuário e retorna False se houver erros.
    """
    try:
        if nome_usuario and senha:
            table_usuarios.insert(nome_usuario=nome_usuario, senha=senha)
            db.commit()
            return True
        else:
            return False
    except:
        return False


def atualizar_pontuacao_jogador(nome_usuario, pontos_partida):
    """
        Atualiza a pontuação de um jogador no banco de dados.
    """
    # busca pelo jogador e calcula sua nova pontuação
    usuario = db(table_usuarios.nome_usuario == nome_usuario).select().first()
    nova_pontuacao = usuario.pontos + pontos_partida
    # atualiza o conjunto de usuários conectados corrigindo a pontuação do jogador
    for usuario_conectado in usuarios_conectados:
        if usuario_conectado[0] == nome_usuario:
            usuarios_conectados.discard(usuario_conectado)
            usuarios_conectados.add(
                (nome_usuario, nova_pontuacao, usuario_conectado[2])
            )
            break
    # atualiza o banco de dados
    db(table_usuarios.nome_usuario == nome_usuario).update(pontos=nova_pontuacao)
    db.commit()


def broadcast_usuarios_conectados():
    for i in CONNECTION_LIST:
        if i != server_socket:
            try:
                # envia a mensagem ao socket
                i.sendall( dumps(usuarios_conectados) )
            except:
                # houve algum erro na conexão com o socket, portanto ele será encerrado
                i.close()
                CONNECTION_LIST.remove(i)


def main():
    print 'Servidor online'
    while True:
        # obtem a lista de sockets que estão prontos para serem lidos
        read_sockets, write_sockets, error_sockets = select(CONNECTION_LIST, [], [])
        for i in read_sockets:
            if i == server_socket:
                # foi realizada uma nova conexão
                conn, addr = server_socket.accept()
                CONNECTION_LIST.append(conn)
                print 'Cliente {addr} conectado'.format(addr=addr)
            else:
                # uma nova mensagem foi recebida
                try:
                    dados = loads(i.recv(1024))
                    if len(dados) == 3 or len(dados) == 4:
                        # o usuário fez um pedido de cadastro ou login
                        opcao, nome_usuario, senha, ip_usuario = dados
                        if opcao == '1':
                            # se o login foi realizado com sucesso, o usuário tem acesso
                            # à lista de usuários conectados
                            if login(nome_usuario, senha, ip_usuario):
                                broadcast_usuarios_conectados()
                            else:
                                i.send( dumps(set()) )
                        elif opcao == '2':
                            i.send( dumps(cadastrar(nome_usuario, senha)) )

                    elif len(dados) == 2:
                        # o usuário finalizou uma partida e sua contagem de pontos deve ser alterada
                        nome_usuario, pontos_partida = dados
                        atualizar_pontuacao_jogador(nome_usuario, pontos_partida)
                        broadcast_usuarios_conectados()

                    elif len(dados) == 1:
                        # se o nome do usuário for encontrado, ele será desconectado
                        nome_usuario = dados[0]
                        for usuario in usuarios_conectados:
                            if usuario[0] == nome_usuario:
                                usuarios_conectados.discard(usuario)
                                i.close()
                                CONNECTION_LIST.remove(i)
                                broadcast_usuarios_conectados()
                                print 'Cliente {addr} desconectado'.format(addr=addr)
                                break

                except:
                    # o usuário se desconectou de maneira abrupta
                    i.close()
                    CONNECTION_LIST.remove(i)
                    print 'Cliente {addr} desconectado'.format(addr=addr)
                    continue


    server_socket.close()
    return 0

if __name__ == '__main__':
    main()
