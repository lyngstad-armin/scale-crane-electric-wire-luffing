# Stewart Platform <br>Wiring Schematics
[Back](../README.md)



## Commisioning/Decommisioning
```mermaid
%%{init: { 'flowchart': { 'nodeSpacing': 30, 'rankSpacing': 100, 'curve': 'linear' } } }%%
flowchart LR
classDef navy fill:#2e3c50,stroke:#5b9bd5,color:#fff
classDef crimson fill:#5c2525,stroke:#5b9bd5,color:#fff
classDef forest fill:#1f3d2b,stroke:#5b9bd5,color:#fff
classDef plum fill:#3b2e50,stroke:#5b9bd5,color:#fff
classDef teal fill:#1f3d3d,stroke:#5b9bd5,color:#fff
classDef amber fill:#5a3a1a,stroke:#5b9bd5,color:#fff
classDef magenta fill:#4a1f3d,stroke:#5b9bd5,color:#fff
classDef olive fill:#4a4a1f,stroke:#5b9bd5,color:#fff
classDef slate fill:#33383f,stroke:#5b9bd5,color:#fff
classDef indigo fill:#2a2a5c,stroke:#5b9bd5,color:#fff
classDef maroon fill:#4a1f2e,stroke:#5b9bd5,color:#fff
classDef umber fill:#3d2b1f,stroke:#5b9bd5,color:#fff
classDef steel fill:#1f3a4a,stroke:#5b9bd5,color:#fff
classDef mustard fill:#4a3f1f,stroke:#5b9bd5,color:#fff

RBPI[<br><br><br><br><br>Raspberry Pi Pico W<br><br><br><br><br><br>]
L1[Leg 1]
L2[Leg 2]
L3[Leg 3]
L4[Leg 4]
L5[Leg 5]
L6[Leg 6]

subgraph DR1[" "]
direction LR
D1
A1
end

subgraph DR2[" "]
direction LR
D2
A2
end

subgraph DR3[" "]
direction LR
D3
A3
end

subgraph DR4[" "]
direction LR
D4
A4
end

subgraph DR5[" "]
direction LR
D5
A5
end

subgraph DR6[" "]
direction LR
D6
A6
end

D1[Driver 1<br>BOB]
D2[Driver 2<br>BOB]
D3[Driver 3<br>BOB]
D4[Driver 4<br>BOB]
D5[Driver 5<br>BOB]
D6[Driver 6<br>BOB]
A1["A4988 1"]
A2["A4988 2"]
A3["A4988 3"]
A4["A4988 4"]
A5["A4988 5"]
A6["A4988 6"]

subgraph BRD[" "]
RBPI
W1[12V]
W2[GND]
USB
end


USB---|USB Micro-B|USB0["USB"]
W2---|WAGO|GND[PSU GND]
W1---|WAGO|12V[PSU 12V]

%%linkStyle 0,1,2,3,4,5 display:none


L1 ---|Connector<br>Marked 1| DR1 --- RBPI --- DR4 ---|Connector<br>Marked 4| L4
L2 ---|Connector<br>Marked 2| DR2 --- RBPI --- DR5 ---|Connector<br>Marked 5| L5
L3 ---|Connector<br>Marked 3| DR3 --- RBPI --- DR6 ---|Connector<br>Unmarked| L6

%%DR1 ---- RBPI
%%DR2 ---- RBPI
%%DR3 ---- RBPI
%%RBPI --- DR4
%%RBPI --- DR5
%%RBPI --- DR6


%%Style
RBPI:::forest
DR1:::crimson
DR2:::crimson
DR3:::crimson
DR4:::crimson
DR5:::crimson
DR6:::crimson
D1:::teal
A1:::indigo
D2:::teal
A2:::indigo
D3:::teal
A3:::indigo
D4:::teal
A4:::indigo
D5:::teal
A5:::indigo
D6:::teal
A6:::indigo
L1:::amber
L2:::amber
L3:::amber
L4:::amber
L5:::amber
L6:::amber
W1:::crimson
W2:::slate
USB:::indigo
USB0:::mustard
GND:::slate
12V:::crimson
```
<br>
<br>
<br>

## Platform GPIO Wiring
*(Note: Please add GPIO numbering)*
```mermaid
%%{init: { 'flowchart': { 'nodeSpacing': 30, 'rankSpacing': 100, 'curve': 'linear' } } }%%
flowchart LR
classDef navy fill:#2e3c50,stroke:#5b9bd5,color:#fff
classDef crimson fill:#5c2525,stroke:#5b9bd5,color:#fff
classDef forest fill:#1f3d2b,stroke:#5b9bd5,color:#fff
classDef plum fill:#3b2e50,stroke:#5b9bd5,color:#fff
classDef teal fill:#1f3d3d,stroke:#5b9bd5,color:#fff
classDef amber fill:#5a3a1a,stroke:#5b9bd5,color:#fff
classDef magenta fill:#4a1f3d,stroke:#5b9bd5,color:#fff
classDef olive fill:#4a4a1f,stroke:#5b9bd5,color:#fff
classDef slate fill:#33383f,stroke:#5b9bd5,color:#fff
classDef indigo fill:#2a2a5c,stroke:#5b9bd5,color:#fff
classDef maroon fill:#4a1f2e,stroke:#5b9bd5,color:#fff
classDef umber fill:#3d2b1f,stroke:#5b9bd5,color:#fff
classDef steel fill:#1f3a4a,stroke:#5b9bd5,color:#fff
classDef mustard fill:#4a3f1f,stroke:#5b9bd5,color:#fff

D1[Driver 1<br> BOB]
D2[Driver 2<br> BOB]
D3[Driver 3<br> BOB]
D4[Driver 4<br> BOB]
D5[Driver 5<br> BOB]
D6[Driver 6<br> BOB]

subgraph RBPI[Raspberry Pi Pico W]
    GPX1
    GPX2
    GPX3
    GPX4
    GPX5
    GPX6
    GPX7
    GPX8
    GPX9
    GPX10
    GPX11
    GPX12
end

GPX1 --- GPX7
GPX2 --- GPX8
GPX3 --- GPX9
GPX4 --- GPX10
GPX5 --- GPX11
GPX6 --- GPX12
linkStyle 0,1,2,3,4,5 display:none

D1 ---|PUL| GPX1
D1 ---|DIR| GPX2

D2 ---|PUL| GPX3
D2 ---|DIR| GPX4

D3 ---|PUL| GPX5
D3 ---|DIR| GPX6

GPX7 ---|PUL| D4
GPX8 ---|DIR| D4


GPX9 ---|PUL| D5
GPX10 ---|DIR| D5


GPX11 ---|PUL| D6
GPX12 ---|DIR| D6


%%Style
D1:::teal
D2:::teal
D3:::teal
D4:::teal
D5:::teal
D6:::teal
RBPI:::forest
GPX1:::plum
GPX2:::maroon
GPX3:::plum
GPX4:::maroon
GPX5:::plum
GPX6:::maroon
GPX7:::plum
GPX8:::maroon
GPX9:::plum
GPX10:::maroon
GPX11:::plum
GPX12:::maroon

%%Name
GPX1["GP"]
GPX2["GP"]
GPX3["GP"]
GPX4["GP"]
GPX5["GP"]
GPX6["GP"]
GPX7["GP"]
GPX8["GP"]
GPX9["GP"]
GPX10["GP"]
GPX11["GP"]
GPX12["GP"]
```
<br>
<br>
<br>

## Platform Power Wiring
```mermaid
%%{init: { 'flowchart': { 'nodeSpacing': 30, 'rankSpacing': 100, 'curve': 'linear' } } }%%
flowchart TB
classDef navy fill:#2e3c50,stroke:#5b9bd5,color:#fff
classDef crimson fill:#5c2525,stroke:#5b9bd5,color:#fff
classDef forest fill:#1f3d2b,stroke:#5b9bd5,color:#fff
classDef plum fill:#3b2e50,stroke:#5b9bd5,color:#fff
classDef teal fill:#1f3d3d,stroke:#5b9bd5,color:#fff
classDef amber fill:#5a3a1a,stroke:#5b9bd5,color:#fff
classDef magenta fill:#4a1f3d,stroke:#5b9bd5,color:#fff
classDef olive fill:#4a4a1f,stroke:#5b9bd5,color:#fff
classDef slate fill:#33383f,stroke:#5b9bd5,color:#fff
classDef indigo fill:#2a2a5c,stroke:#5b9bd5,color:#fff
classDef maroon fill:#4a1f2e,stroke:#5b9bd5,color:#fff
classDef umber fill:#3d2b1f,stroke:#5b9bd5,color:#fff
classDef steel fill:#1f3a4a,stroke:#5b9bd5,color:#fff
classDef mustard fill:#4a3f1f,stroke:#5b9bd5,color:#fff

D1[Driver 1<br> BOB]
D2[Driver 2<br> BOB]
D3[Driver 3<br> BOB]
D4[Driver 4<br> BOB]
D5[Driver 5<br> BOB]
D6[Driver 6<br> BOB]



subgraph PSU
    GND[Common GND]
    12V
end

subgraph DRV[" "]
    D1
    D2
    D3
    D4
    D5
    D6
end

subgraph RB["Raspberry Pi Pico W"]
    VBUS[VBUS<br>5V]
    USB
    3.3V
    GN[GND]
end




GND ---|To all BOB| D1 & D4 %%0,1
12V ---|To all BOB| D1 & D4 %%2,3
D3 & D6 ---|To all BOB| VBUS %%4,5
GND --- GN %%6

linkStyle 0,1,6 stroke:#2A2A2A,stroke-width:5px
linkStyle 2,3,4,5 stroke:#FF4D4D,stroke-width:4px
USB --- USB0["USB"]
linkStyle 7 stroke:#4a4,stroke-width:6px

D1 --- D2 --- D3
D4 --- D5 --- D6


%%style
12V:::crimson
VBUS:::crimson
GND:::slate
GN:::slate
RB:::forest
USB:::indigo
USB0:::mustard
3.3V:::crimson
PSU:::navy
DRV:::steel
D1:::teal
D2:::teal
D3:::teal
D4:::teal
D5:::teal
D6:::teal
```