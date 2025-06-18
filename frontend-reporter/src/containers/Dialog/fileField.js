import React from "react";

class FileField extends React.Component {
    state = { fileInfo: null }
    // TODO: drag&drop

    // onChange(date, changed) {
    //     if (changed) {
    //         this.props.onChange(this.formatDate(date));
    //     }
    // }

    onChange(event) {
        if(event.target.files.length === 0) {
            this.props.onChange(null);
            return;
        }
        let fileName = event.target.value;
        let startIndex = (fileName.indexOf('\\') >= 0 ? fileName.lastIndexOf('\\') : fileName.lastIndexOf('/'));
        fileName = fileName.substring(startIndex + 1);
        let reader = new FileReader();
        reader.onload = ev => {
            let data = ev.target.result;
            if(!data.startsWith('data:')) {
                return;
            }
            data = data.substring(5).split(';')
            let result = {
                "filename": fileName,
                "contentType": data[0],
                "content": data[1].split(',')[1],
            }
            this.props.onChange(result);
        }
        reader.readAsDataURL(event.target.files[0]);
    }

    render() {

        return (<div className={"fileField"}>
            <input type={"file"} onChange={event => { this.onChange(event) }}/>
            { this.state.fileInfo ? <span className={"fileInfo"}>{this.state.fileInfo}</span> : null }
        </div>);
    }

}

export default FileField;