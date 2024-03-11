Popa Bianca

Implementare Switch

1. Tabela de comutare

    Algoritmul pentru tabela de comutare respecta pseudocodul din enuntul temei.
Am initializat un dictionar MAC_Table care va retine corespondentele dintre MAC-ul
sursei si interfata pe care aceasta a venit. Apoi, avem cazurile:
    - multicast - este identificat prin faptul ca primul octet este impar
                - se face flooding pe toate porturile in afara de cel pe care a venit
    - broadcast - este identificat prin faptul ca primul octet este ff (impar), deci
                va fi tratat in acelasi caz cu multicastul
                - se face flooding pe toate porturile in afara de cel pe care a venit
    - unicast - se verifica daca MAC-ul destinatiei este in tabela MAC_Table
                daca da, atunci se trimite pachetul pe portul corespunzator
                daca nu, se face flooding pe toate porturile in afara de cel pe care a 
                venit

2. VLAN
    
    Pentru a implementa VLAN-ul, am modificat codul de la prima cerinta, adaugand cele 
4 cazuri posibile la fiecare tip de adresa MAC:
    - primeste de la trunk, trimite catre trunk
    Nu se modifica nimic
    - primeste de la trunk, trimite catre access
    Se verifica daca VLAN-ul din tag este egal cu cel al portului de tip access. Daca da,
    se trimite pachetul fara tag. Daca nu, pachetul nu este trimis.
    - primeste de la access, trimite catre trunk
    Se creeaza tagul ce contine VLAN-ul portului de tip access, se adauga la pachet si se
    trimite.
    - primeste de la access, trimite catre access
    Se verifica daca cele doua porturi au acelasi VLAN. Daca da, pachetul este trimis.

3. STP

    Algoritmul pentru STP respecta pseudocodul din enuntul temei. Astfel, avem 4 modificari
de facut:
    - initializarea: se initializeaza toate valorile specifice switchului curent. SW_States
    retine tipul fiecarui port (designated - blocking) si SW_Result retine starea acestuia
    (listening - blocking). Daca portul este root, atunci toate porturile sale sunt setate 
    ca designated.
    - trimiterea pachetelor BPDU: doar switchul root poate trimite pachete BDPU. Acesta
    va trimite pachetele pe toate porturile sale o data pe secunda. Inainte sa se trimita un
    pachet, acesta este creat in formatul:

        DST_MAC|SRC_MAC|LLC_LENGTH|LLC_HEADER|BPDU_HEADER|BPDU_CONFIG

    class bpdu() - este folosita pentru crearea bdpu_config
    class root() - stabileste rootul topologiei 

    - primirea pachetelor BPDU: daca pachetul are un root_bridge_ID mai mic decat al switchului
    curent, atunci switchul de la care am primit este considerat root si vom trimite pachetul pe 
    toate celelalte porturi. Altfel, daca switchul are root_bridge_ID egal, sunt urmate toate 
    cazurile din pseudocod.
    - trimiterea celorlalte pachete: in cazul porturilor de tip trunk, pachetul se trimite
    doar daca acesta are starea "LISTENING"