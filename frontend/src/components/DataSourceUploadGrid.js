// Last reviewed: 2025-04-29 07:31:24 UTC (User: TeeksssLogin)
import React from 'react';
import AddDataSource from './AddDataSource';
import ImageUpload from './ImageUpload';
import PdfUpload from './PdfUpload';
import WebsiteUpload from './WebsiteUpload';
import PostgreSqlUpload from './PostgreSqlUpload';
import MySqlUpload from './MySqlUpload';
import MongoDbUpload from './MongoDbUpload';
import SqliteUpload from './SqliteUpload';
import GoogleDriveUpload from './GoogleDriveUpload';
import DropboxUpload from './DropboxUpload';
import EmailUpload from './EmailUpload';
import SocialMediaUpload from './SocialMediaUpload';
import './DataSourceUploadGrid.css';

const DataSourceUploadGrid = ({ onUploadSuccess, onUploadError, apiRequest }) => {
  // Ortak proplar
  const commonUploadProps = {
    onUploadSuccess,
    onUploadError,
    apiRequest
  };

  return (
    <div className="data-source-uploads">
      <h3>Yeni Veri Kaynağı Ekle</h3>
      <div className="upload-grid">
        <div className="upload-component">
          <AddDataSource {...commonUploadProps} sourceName="Manuel" />
        </div>
        <div className="upload-component">
          <ImageUpload {...commonUploadProps} sourceName="Resim" />
        </div>
        <div className="upload-component">
          <PdfUpload {...commonUploadProps} sourceName="PDF" />
        </div>
        <div className="upload-component">
          <WebsiteUpload {...commonUploadProps} sourceName="Website" />
        </div>
        <div className="upload-component">
          <GoogleDriveUpload {...commonUploadProps} sourceName="Google Drive" />
        </div>
        <div className="upload-component">
          <DropboxUpload {...commonUploadProps} sourceName="Dropbox" />
        </div>
        <div className="upload-component">
          <PostgreSqlUpload {...commonUploadProps} sourceName="PostgreSQL" />
        </div>
        <div className="upload-component">
          <MySqlUpload {...commonUploadProps} sourceName="MySQL" />
        </div>
        <div className="upload-component">
          <MongoDbUpload {...commonUploadProps} sourceName="MongoDB" />
        </div>
        <div className="upload-component">
          <SqliteUpload {...commonUploadProps} sourceName="SQLite" />
        </div>
        <div className="upload-component">
          <EmailUpload {...commonUploadProps} sourceName="Email" />
        </div>
        <div className="upload-component">
          <SocialMediaUpload {...commonUploadProps} sourceName="Sosyal Medya" />
        </div>
      </div>
    </div>
  );
};

export default DataSourceUploadGrid;