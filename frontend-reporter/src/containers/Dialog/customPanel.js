import React from "react";
import renderCustomPanel from "../../custom/all";

class CustomPanel extends React.Component {
    // TODO: w tej klasie podrutować żądania interfejsu z danymi wystawianymi po stronie pythonga
    render() {
        return renderCustomPanel(this.props);
    }
}

export default CustomPanel;