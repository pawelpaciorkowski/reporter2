import React from "react";
import {Switch} from "@blueprintjs/core";


export type EventFilterSettings = {
    domains: string[],
    services: string[],
    showTransactions: boolean,
    allEventsFromTransaction: boolean,
}

interface EventFilterProps {
    filter: EventFilterSettings,
    setFilter: (value: EventFilterSettings) => void,
    domains: string[],
    services: string[],
    serviceTitles: string[],
}

interface FilterButtonsProps {
    caption: string,
    allValues: string[],
    allTitles?: string[],
    selectedValues: string[],
    addValue: (value: string) => void,
    removeValue: (value: string) => void,
    clear: () => void,
}

const FilterButtons = ({caption, allValues, allTitles, selectedValues, addValue, removeValue, clear}: FilterButtonsProps) => {
    let filterClasses = ['filter'];
    if (selectedValues.length > 0) {
        filterClasses.push('filterActive');
    }
    return (<div className={filterClasses.join(' ')}>
        {selectedValues.length > 0 ? <span onClick={clear}>{caption}:</span> : <>{caption}:</>}
        {allValues.map((value, i) => {
            let title = allTitles ? allTitles[i] : value
            if(selectedValues.indexOf(value) !== -1) {
                return <span className="option selected" onClick={() => removeValue(value)}>{title}</span>
            } else {
                return <span className="option" onClick={() => addValue(value)}>{title}</span>
            }
        })}
    </div>)

}

export const RepublikaEventFilter = ({filter, setFilter, domains, services, serviceTitles}: EventFilterProps) => {
    return (<div className="republikaEventFilter">
        <FilterButtons caption={"Dziedziny"} allValues={domains} selectedValues={filter.domains}
                       addValue={value => setFilter({...filter, domains: filter.domains.concat([value])})}
                       removeValue={value => {
                           setFilter({...filter, domains: filter.domains.filter(existing => existing !== value)})
                       }}
                       clear={() => setFilter({...filter, domains: []})}
        />
        <FilterButtons caption={"Usługi"} allValues={services} selectedValues={filter.services} allTitles={serviceTitles}
                       addValue={value => setFilter({...filter, services: filter.services.concat([value])})}
                       removeValue={value => {
                           setFilter({...filter, services: filter.services.filter(existing => existing !== value)})
                       }}
                       clear={() => setFilter({...filter, services: []})}
        />
        {/*<InputGroup>*/}
            <Switch label="Grupuj transakcje"
                    checked={filter.showTransactions}
                    onChange={e => {
                        const checked = (e as React.ChangeEvent<HTMLInputElement>).target.checked;
                        if(checked) {
                            setFilter({...filter, showTransactions: true})
                        } else {
                            setFilter({...filter, showTransactions: false, allEventsFromTransaction: false})
                        }
                    }}
                    inline />
            { filter.showTransactions ? <Switch
                    label="Wszystkie zdarzenia z transakcji"
                    checked={filter.allEventsFromTransaction}
                    onChange={e => setFilter({...filter, allEventsFromTransaction: (e as React.ChangeEvent<HTMLInputElement>).target.checked})}
                    inline/> : null }
        {/*</InputGroup>*/}

    </div>)

}
