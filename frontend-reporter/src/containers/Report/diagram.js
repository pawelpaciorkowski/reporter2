import React from "react";
import {VerticalBarSeries, XYPlot, HorizontalGridLines, VerticalGridLines, XAxis, YAxis} from "react-vis";
import "react-vis/dist/style.css";

class ReportDiagram extends React.Component {
    renderBars() {
        let desc = this.props.desc;
        let data = [];
        for(var row of desc.data) {
            data.push({x: row[0], y: row[1]});
        }
        return (<XYPlot width={desc.width || 600} height={desc.height || 300}>
            <VerticalGridLines />
            <HorizontalGridLines />
            <VerticalBarSeries
                color={'#059bd7'}
                data={data} />
            <XAxis title={desc.x_axis_title}/>
            <YAxis title={desc.y_axis_title} />
        </XYPlot>);
    }


    render() {
        let desc = this.props.desc;
        let subtype = desc.subtype;
        return (<div>
            {desc.title ? <h4 className="reportTabletitle">{desc.title}</h4> : null}
            {subtype === 'bars' ? this.renderBars() : null}
        </div>);
    }
}

export default ReportDiagram;

/*

Śmieci: jeśli się nie odświeża widok, to zwiększyć ilość obserwowanych plików
https://create-react-app.dev/docs/troubleshooting/#npm-start-doesnt-detect-changes

dodanie tego jednego wykresu zwiększyło rozmiar zbudowanego frontendu z ~240 do 323.53 KB,
budowanie przestało się mieścić na luzie w pamięci

 */