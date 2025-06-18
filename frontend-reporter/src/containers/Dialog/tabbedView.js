import React from "react";
import {Tabs, Tab} from "@blueprintjs/core";

class TabbedView extends React.Component {
    state = {
        value: this.props.values[this.props.defaultTab || 0],
    };

    getValue() {
        return this.state.value;
    }

    render() {
        let tabs = [];
        for(let i=0; i<this.props.titles.length; i++) {
            tabs.push(
                <Tab id={'tab_' + i} key={i}
                      title={this.props.titles[i]}
                      panel={this.props.panels[i]}
                />
            );
        }
        return (
            <Tabs
                animate={false}
                renderActiveTabPanelOnly={true}
                vertical={this.props.vertical}
                defaultSelectedTabId={'tab_' + this.props.defaultTab}
                onChange={(val) => this.handleChange(val)}
                large={this.props.large}
            >
                {tabs}
            </Tabs>
        );
    }

    handleChange(val) {
        // TODO: w val dostajemy id taba; chcemy sprawdzić czy całość ma fielda i ew. nanieść zmianę
        let tab_id = val.split('_');
        let value = this.props.values[parseInt(tab_id[1])];
        this.setState({value: value});
    }
    // TODO: pamiętać w jakimś stanie aktywny panel, żeby tylko z niego zbierać wartości
    // TODO: zadbać o unikalność, jeśli miałoby być więcej poziomów
}

export default TabbedView;