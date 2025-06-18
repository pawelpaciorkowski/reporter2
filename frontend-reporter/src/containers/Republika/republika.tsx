import React, {useState} from "react";
import "./republika.css";
import {EventFilterSettings, RepublikaEventFilter} from "./filter";

/*
    TODO do sprawdzenia w generowaniu zdarzeń
    BELCHAT:496023:
        + CntWykZmianaMaterialu emitowane mimo że materiał był wcześniej ustawiony w CntWykUtworzone
        + CntWykZmianaPlatnika emitowane mimo płatnika zgodnego z CntZlecDaneRejestracyjne, w tej samej transakcji. Powinno sprawdzać zgodność
        -/+ CntWykZmianaOdplatnosci - płatne i na koszt labu - sprawdzić - wygląda że koszty=1 nie znaczy na koszt labu
        + CntWykPowtorka - wpada przy wykonaniu z liczba_powtorzen=1
        + CntWykDystrybucja - wpada wielokrotnie - prawdopodobnie złe działanie cache

transakcja 3935631 - odesłanie wyniku z zawodzia

window.reload(true)
 */


const MAIN_DETAILS: { [k: string]: string[] } = {
    'CntZlecUtworzone': ['system', 'sys_id'],
    'CntZlecRejestracjaBezNumeru': ['data_rejestracji', 'kodkreskowy', 'zewnetrzny_identyfikator', 'kanal_internetowy'],
    'CntZlecRejestracjaZNumerem': ['data_rejestracji', 'numer', 'kodkreskowy', 'zewnetrzny_identyfikator', 'kanal_internetowy'],
    'CntZlecKomentarz': ['komentarz'],
    'CntZlecDrukowanyOpis': ['opis'],
    'CntZlecWewnetrznaNotatka': ['notatka'],
    'CntZlecDaneRejestracyjne': [
        'platnik', 'zleceniodawca', 'typ_zlecenia',
        'pacjent', 'lekarz',
        'dzm', 'waga', 'miejsceodeslania', 'opismiejscaodeslania',
        'kodkreskowy', 'obcykodkreskowy', 'zewnetrzny_identyfikator',
    ],
    'CntZlecNadanieNumeruDziennego': [
        'data_reejstracji', 'numer',
    ],
    'CntWykUtworzone': ['system', 'sys_id', 'powtorka', 'jest_pakietem', 'jest_skladowa'],
    'CntWykPodpieciePodPakiet': ['pakiet_symbol'],
    'CntWykZmianaMetody': ['pracownia', 'metoda', 'aparat'],
    'CntWykPobrane': ['poborca'],
    'CntWykDystrybucja': ['material', 'kodkreskowy'],
    'CntWykZmianaMaterialu': ['material'],
    'CntWykZmianaPlatnika': ['platnik_zlecenia', 'platnik_wykonania', 'zgodny'],
    'CntWykZmianaOdplatnosci': ['platne', 'na_koszt_labu', 'koszt', 'punkty'], // TODO: w przyładzie i płatne i na koszt labu
    'CntWykIdentyfikatorNadanie': ['identyfikator'],
    'CntWykKodKreskowyNadanie': ['kodkreskowy'],
    'CntWykWykonanie': ['dane_wykonania', 'wyniki', 'akredytacja'],
    'CntWykAkceptacja': ['dane_wykonania', 'wyniki', 'akredytacja'],
    'CntWykBladWykonania': ['blad_wykonania'],
    'CntWykWycenaWLab': ['cena', 'cennik', 'stawka_vat'],
    'CntWykModyfikacjaWynikow': ['wyniki'],
    'CntWykKodKreskowyModyfikacja': ['kodkreskowy'],
    'CntWykZatwierdzenie': ['dane_wykonania', 'wyniki', 'bardzo_zatwierdzone', 'akredytacja'],
    'CntWykRozliczenie': ['platne', 'koszty', 'platnik', 'zleceniodawca', 'data_rozliczeniowa', 'inny_platnik_wykonania'], // TODO: czy nie zmeinić koszty na na_koszt_labu?
    'CntWykPowtorka': ['liczba_powtorzen'],
    'CntWykListaRobocza': ['statyw', 'polozenie_x', 'polozenie_y', 'lista_robocza'],
    'CntWykCzynnoscTechniczna': ['rodzaj', 'czynnosc'], // TODO: czynnosc do wywalenia - docelowo rodzaj tak jak w innych miejscach

    'CntWydrOdebrany': ['odebral', 'plik', 'sciezka'],
    'CntWydrCzynnoscTechniczna': ['rodzaj'],

    'CntZewZlecenieKomunikacja': ['rodzaj'],
    'CntZewZlecenieParametry': ['parametry'],
    'CntZewZlecenieChange': ['status'],
    'CntZewZlecenieIdent': ['system', 'numer', 'oddzial', 'pacjent'],
    'CntZewWykonanieParametry': ['parametry'],
    'CntZewWykonanieChange': ['status'],
    'CntZewWykonanieKomunikacja': ['rodzaj'],

    'platnik': ['symbol', 'nazwa', 'nip', 'gotowkowy'],
    'zleceniodawca': ['symbol', 'nazwa', 'platnik', 'gotowkowy'],
    'pacjent': ['nazwisko', 'imiona', 'pesel', 'data_urodzenia', 'plec'],
    'lekarz': ['nazwisko', 'imiona', 'numer', 'specjalizacja'],
    'poborca': ['nazwisko', 'imiona', 'hl7sysid'],
    'dane_wykonania': ['badanie', 'metoda', 'pracownia', 'aparat'],
    'badanie': ['symbol', 'nazwa'],
    'metoda': ['symbol', 'nazwa'],
    'pracownia': ['symbol', 'nazwa'],
    'aparat': ['symbol', 'nazwa'],
    'wyniki': ['parametr', 'wynik_tekstowy', 'wynik_liczbowy', 'flaga', 'norma_tekst', 'ukryty'],
    'parametr': ['symbol', 'nazwa'],

    'parametry': ['Kod systemu', 'Drugi kod systemu', 'IDNadrzednego', 'GodzinaRejestracji',
        'Pacjent', 'Imiona', 'Nazwisko', 'Plec', 'Adres', 'PESEL', 'DataUrodzenia', 'email', 'telefon',
        'Lekarz', 'ImionaLekarza', 'NazwiskoLekarza', 'TytulLekarza', 'NrPrawaWykZawLekarza',
        'Pobyt', 'Uwagi',
        'Ksiega', 'Termin', 'Pilnosc', 'Platnik', 'PlatnikNazwa', 'Oddzial', 'OddzialNazwa',
        'KodKreskowy', 'ObcyKodKreskowy', 'dodatkowyidentyfikator',
        'MiejsceOdeslaniaWyniku',
        'Badanie', 'Nazwa usługi', 'Kod usługi', 'ID usługi',
        'Material', 'Materiał', 'Nazwa materiału', 'Kod materiału', 'ID materiału',
        'Godzina', 'IDPobierajacego', 'NazwiskoPobierajacego', 'ImionaPobierajacego', 'TytulPobierajacego',
    ],

}

const FIELD_TITLES: { [k: string]: string } = {
    'system': 'system źródłowy',
    'sys_id': 'id w systemie źródłowym',
    'kodkreskowy': 'kod kreskowy',
    'data_rejestracji': 'data rejestracji',
    'platnik': 'płatnik',
    'platnik_zlecenia': 'płatnik zl.',
    'platnik_wykonania': 'płatnik wyk.',
    'typ_zlecenia': 'typ zlecenia',
    'miejsceodeslania': 'miejsce odesłania wyniku',
    'powtorka': 'powtórka',
    'jest_pakietem': 'jest pakietem',
    'jest_skladowa': 'jest składową',
    'platne': 'płatne',
    'na_koszt_labu': 'na koszt labu',
    'dane_wykonania': 'dane wykonania',
    'bardzo_zatwierdzone': 'bardzo zatwierdzone',
    'data_rozliczeniowa': 'data rozl.',
    'gotowkowy': 'gotówkowy',
    'pakiet_symbol': 'pakiet',

    'data_urodzenia': 'data ur.',
    'plec': 'płeć',
    'lista_robocza': 'lista robocza',
    'polozenie_x': 'położenie x',
    'polozenie_y': 'położenie y',
}

const FIELDS_NEWLINE: string[] = [
    'pacjent', 'lekarz', 'dane_wykonania',
];

const FIELDS_LIST: string[] = [
    'wyniki'
]

export interface RepublikaEvent {
    id: number,
    src: string,
    trans_id: number,
    src_ts?: string,
    repl_ts?: string,
    event_ts?: string,
    domain_name: string,
    order_id?: string | null,
    order_item_id?: string | null,
    entity_name?: string | null,
    entity_id?: string | null,
    event_type: string,
    event_data: { [k: string]: any },
}

export interface EventStreamDefinition {
    events: RepublikaEvent[],
    lookup: { [k: string]: { [k: string]: string | null } }
}

type TransactionOfEvents = {
    trans_id: number,
    events: RepublikaEvent[],
    description: string[],
    src?: string,
    timestamp?: string,
    pracownicy: string[],
}

export interface RepublikaEventStreamViewProps {
    eventStream: EventStreamDefinition,
}

export interface EventViewProps {
    event: RepublikaEvent,
    service?: string,
    unrelated: boolean;
}

const EventView = ({event, service, unrelated}: EventViewProps) => {
    const [showDetails, setShowDetails] = useState<boolean>(false)
    const toggleDetails = () => {
        setShowDetails(!showDetails)
    }
    let mainClasses = ['event']
    if (unrelated) {
        mainClasses.push('eventUnrelated')
    }

    const formatDetails = (name: string, data: { [k: string]: any } | string | number | boolean): string | React.ReactNode => {
        if (typeof data === 'string') {
            return data
        }
        if (typeof data === 'number') {
            return data.toString()
        }
        if (typeof data === 'boolean') {
            return data ? 'T' : 'N'
        }
        if (Array.isArray(data)) {
            if(FIELDS_LIST.indexOf(name) !== -1) {
                return (<ul>
                    {data.map(item => <li>{formatDetails(name, item)}</li>)}
                </ul>)
            } else {
                return data.map(item => formatDetails(name, item))
            }
        }
        if (!MAIN_DETAILS.hasOwnProperty(name)) {
            return 'BRAK OPISU DLA ' + name + '!!!'
        }
        return MAIN_DETAILS[name].filter(
            fld => data.hasOwnProperty(fld) && data[fld] !== null && data[fld] !== "" && !(Array.isArray(data[fld]) && data[fld].length === 0)
        ).map(fld => {
            let spanClassess: string[] = ["field"];
            if(FIELDS_NEWLINE.indexOf(fld) !== -1) {
                spanClassess.push('fieldNewLine')
            }
            return (<span className={spanClassess.join(' ')}>
                <span className="fieldTitle">{FIELD_TITLES.hasOwnProperty(fld) ? FIELD_TITLES[fld] : fld}:</span>
                <span className="fieldValue">{formatDetails(fld, data[fld])}</span>
            </span>);
        })
    }

    return (<div className={mainClasses.join(' ')}>
        <h4 onClick={toggleDetails}>
            <span className="domainName">{event.domain_name} </span>
            <span className="eventType">{event.event_type} </span>
            <span className="eventTimestamp">{event.event_ts} </span>
            {service ? <span className="serviceName"> {service}</span> : null}
        </h4>
        {MAIN_DETAILS.hasOwnProperty(event.event_type) ? <div className="eventMainDetails">
            {formatDetails(event.event_type, event.event_data)}
        </div> : null}
        {showDetails ? <div className="eventDetails">{JSON.stringify(event)}</div> : null}
    </div>)
}


export const RepublikaEventStreamView = ({eventStream}: RepublikaEventStreamViewProps) => {
    const [filter, setFilter] = useState<EventFilterSettings>({
        domains: [],
        services: [],
        showTransactions: true,
        allEventsFromTransaction: false
    }); // TODO przywrócić wartości domyślne

    let domains = [...new Set(eventStream.events.map(ev => ev.domain_name))];
    let services: string[] = [];
    let order_item_ids: { [k: string]: string[] } = {};
    let order_item_nadrzedne: { [k: string]: string } = {};
    let services_in_order_items: { [k: string]: string } = {};
    let services_in_external_order_items: { [k: string]: string } = {};
    eventStream.events.map(ev => {
        if (ev.event_type === 'CntWykUtworzone' || ev.event_type === 'CntWykOdkryte') {
            let bad_mat = [ev.event_data['badanie']];
            if (ev.event_data['material']) {
                bad_mat.push(ev.event_data['material']);
            }
            let bad_mat_s = bad_mat.join(':')
            if (services.indexOf(bad_mat_s) === -1) {
                services.push(bad_mat_s);
                order_item_ids[bad_mat_s] = [];
            }
            if (ev.order_item_id) {
                order_item_ids[bad_mat_s].push(ev.order_item_id)
                services_in_order_items[ev.order_item_id] = bad_mat_s
                if (ev.event_data['nadrzedne']) {
                    order_item_nadrzedne[ev.order_item_id] = ev.event_data['nadrzedne']
                }
            }
        }
        if (ev.event_type === 'CntZewWykonanieBind' || ev.event_type === 'CntZewWykonanieRebind') {
            if (ev.order_item_id && services_in_order_items.hasOwnProperty(ev.order_item_id)) {
                const service = services_in_order_items[ev.order_item_id];
                if (ev.event_data.hasOwnProperty('wykzew_id')) {
                    services_in_external_order_items[ev.event_data['wykzew_id']] = service;
                }
            }
        }
        return null;
    });

    // let transactions = [...new Set(eventStream.events.map(ev => ev.trans_id))].sort();

    let visibleEvents = eventStream.events;

    if (filter.services.length > 0) {
        let selected_order_item_ids: string[] = [];
        filter.services.map(service => {
            if (order_item_ids.hasOwnProperty(service)) {
                selected_order_item_ids.push(...order_item_ids[service])
            }
            return null
        })
        visibleEvents = visibleEvents.filter(ev => ev.order_item_id && selected_order_item_ids.indexOf(ev.order_item_id) !== -1)
    }

    if (filter.domains.length > 0) {
        visibleEvents = visibleEvents.filter(ev => filter.domains.indexOf(ev.domain_name) !== -1);
    }
    const serviceNameForEvent = (ev: RepublikaEvent): string | undefined => {
        if (ev.order_item_id && services_in_order_items.hasOwnProperty(ev.order_item_id)) {
            let res = services_in_order_items[ev.order_item_id];
            if(order_item_ids[res].length > 1) {
                res += ' (' + (order_item_ids[res].indexOf(ev.order_item_id) + 1).toString() + ')'
            }
            if(order_item_nadrzedne.hasOwnProperty(ev.order_item_id)) {
                res += ' (z: ' + services_in_order_items[order_item_nadrzedne[ev.order_item_id]] + ')'
            }
            return res
        }
        if (ev.event_data.hasOwnProperty('wykzew_id') && services_in_external_order_items.hasOwnProperty(ev.event_data['wykzew_id'])) {
            return services_in_external_order_items[ev.event_data['wykzew_id']];
        }
        return undefined;
    }


    let res = [];
    res.push(<RepublikaEventFilter filter={filter} setFilter={setFilter}
                                   domains={domains}
                                   services={services}
                                   serviceTitles={services.map(s => order_item_ids[s].length === 1 ? s : s + '*')}/>)
    res.push(<h5>Zdarzenia</h5>)
    if (filter.showTransactions) {
        let transactionsOfEvents: TransactionOfEvents[] = [];
        let transactions: { [k: number]: number } = {};
        visibleEvents.map(ev => {
            if (!transactions.hasOwnProperty(ev.trans_id)) {
                transactionsOfEvents.push({
                    trans_id: ev.trans_id, events: [], description: ['Transakcja ' + ev.trans_id],
                    src: ev.src, timestamp: ev.src_ts, pracownicy: [],
                })
                transactions[ev.trans_id] = transactionsOfEvents.length - 1;
            }
            transactionsOfEvents[transactions[ev.trans_id]].events.push(ev);
            if (ev.event_data.hasOwnProperty('pracownik') && ev.event_data['pracownik'] !== null) {
                const prac = ev.event_data['pracownik']
                if (transactionsOfEvents[transactions[ev.trans_id]].pracownicy.indexOf(prac) === -1) {
                    transactionsOfEvents[transactions[ev.trans_id]].pracownicy.push(prac)
                }
            }
            // TODO: opisy i inne takie
            return null
        })
        for (const trans_id in transactions) {
            const idx = transactions[trans_id];
            const toe = transactionsOfEvents[idx];
            toe.pracownicy.map(prac => {
                if (eventStream.lookup.hasOwnProperty('pracownicy') && eventStream.lookup['pracownicy'].hasOwnProperty(prac)) {
                    const pracDesc = eventStream.lookup['pracownicy'][prac]
                    if (pracDesc !== null) {
                        toe.description.push(pracDesc)
                    }
                }
                return null
            })
            let eventViews: React.ReactNode[] = [];
            if (filter.allEventsFromTransaction) {
                const relatedIds = new Set(toe.events.map(ev => ev.id))
                eventStream.events.filter(ev => (ev.trans_id.toString() === trans_id)).map(ev => {
                    const related = relatedIds.has(ev.id);
                    eventViews.push(<EventView event={ev} unrelated={!related}
                                               service={serviceNameForEvent(ev)}/>)
                    return null
                })
            } else {
                toe.events.map(ev => {
                    eventViews.push(<EventView event={ev} unrelated={false}
                                               service={serviceNameForEvent(ev)}/>)
                    return null
                })
            }
            res.push(<div className="transaction">
                <div className="transactionInfo">
                    {toe.src} <strong>{toe.timestamp}</strong>
                    <div className="transactionInfoRight">
                        {toe.description.map(s => <span>{s}</span>)}
                    </div>
                </div>
                <div className="transactionEvents">
                    {eventViews}
                </div>
            </div>)
        }
    } else {
        res.push(...visibleEvents.map(ev => <EventView event={ev} unrelated={false}
                                                       service={serviceNameForEvent(ev)}/>));
    }
    return (<div>
        {res}
    </div>);

}
