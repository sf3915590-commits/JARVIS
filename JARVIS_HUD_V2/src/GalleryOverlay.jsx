import React from "react";

export default function GalleryOverlay({ open, images, onClose, onAdd }) {
  if (!open) return null;
  return (
    <div className="jarvis-gallery-backdrop" role="dialog" aria-modal="true" aria-label="JARVIS Gallery">
      <section className="jarvis-gallery-panel">
        <div className="jarvis-gallery-header">
          <div><small>JARVIS</small><h2>GALLERY</h2></div>
          <button type="button" onClick={onClose}>CLOSE</button>
        </div>
        {images.length ? (
          <div className="jarvis-gallery-grid">
            {images.map((image) => (
              <figure key={`${image.name}-${image.url}`}>
                <img src={image.url} alt={image.name} />
                <figcaption>{image.name}</figcaption>
              </figure>
            ))}
          </div>
        ) : (
          <div className="jarvis-gallery-empty">
            <div>NO IMAGES LOADED</div>
            <small>Choose images from your Windows Gallery.</small>
          </div>
        )}
        <button type="button" className="jarvis-gallery-add" onClick={onAdd}>ADD IMAGES</button>
      </section>
    </div>
  );
}
