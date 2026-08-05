"use client";

import React, { useState, useEffect } from "react";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Loader2, Camera } from "lucide-react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";

interface EditarPerfilModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initialData: {
    nombre: string;
    email: string;
    nroMatricula: string;
    escribaniaNombre: string;
    avatar_url?: string;
  };
  onSave: (datos: {
    nombre: string;
    email: string;
    nroMatricula: string;
    escribaniaNombre: string;
  }) => Promise<void>;
  onSaveAvatar?: (file: File) => Promise<void>;
}

export function EditarPerfilModal({ open, onOpenChange, initialData, onSave }: EditarPerfilModalProps) {
  const [form, setForm] = useState(initialData);
  const [guardando, setGuardando] = useState(false);

  useEffect(() => {
    if (open) {
      setForm(initialData);
    }
  }, [open, initialData]);

  const handleSave = async () => {
    setGuardando(true);
    try {
      if (avatarFile && onSaveAvatar) {
        await onSaveAvatar(avatarFile);
      }
      await onSave(form);
      setAvatarFile(null);
      setAvatarPreview(null);
      onOpenChange(false);
    } catch (e: any) {
      console.error(e);
    } finally {
      setGuardando(false);
    }
  };

  const [avatarFile, setAvatarFile] = useState<File | null>(null);
  const [avatarPreview, setAvatarPreview] = useState<string | null>(null);

  const handleAvatarChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setAvatarFile(file);
      setAvatarPreview(URL.createObjectURL(file));
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md bg-background border border-border shadow-xl">
        <DialogHeader>
          <DialogTitle>Editar perfil</DialogTitle>
          <DialogDescription>
            Actualiza tu información personal y datos de escribanía.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="flex justify-center mb-6">
            <div className="relative group cursor-pointer" onClick={() => document.getElementById("avatar-upload")?.click()}>
              <Avatar className="h-20 w-20 border-2 border-border">
                <AvatarImage src={avatarPreview || form.avatar_url || ""} />
                <AvatarFallback className="text-xl">{form.nombre?.charAt(0) || "U"}</AvatarFallback>
              </Avatar>
              <div className="absolute inset-0 bg-black/40 rounded-full opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                <Camera className="text-white h-6 w-6" />
              </div>
              <input 
                id="avatar-upload"
                type="file" 
                className="hidden" 
                accept="image/*"
                onChange={handleAvatarChange}
              />
            </div>
          </div>
          <div>
            <label className="text-sm font-medium text-foreground">
              Nombre completo
            </label>
            <Input
              value={form.nombre}
              onChange={(e) => setForm(prev => ({ ...prev, nombre: e.target.value }))}
              placeholder="Tu nombre"
              className="mt-1.5"
            />
          </div>
          <div>
            <label className="text-sm font-medium text-foreground">
              Correo electrónico
            </label>
            <Input
              type="email"
              value={form.email}
              disabled
              placeholder="tu@email.com"
              className="mt-1.5 bg-muted"
              title="El correo no se puede cambiar"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium text-foreground">
                Nro. Matrícula
              </label>
              <Input
                value={form.nroMatricula}
                onChange={(e) => setForm(prev => ({ ...prev, nroMatricula: e.target.value }))}
                placeholder="Ej: 4567"
                className="mt-1.5"
              />
            </div>
            <div>
              <label className="text-sm font-medium text-foreground">
                Escribanía
              </label>
              <Input
                value={form.escribaniaNombre}
                onChange={(e) => setForm(prev => ({ ...prev, escribaniaNombre: e.target.value }))}
                placeholder="Ej: Registro 123"
                className="mt-1.5"
              />
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={guardando}>
            Cancelar
          </Button>
          <Button onClick={handleSave} disabled={guardando}>
            {guardando ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Guardando...</> : "Guardar cambios"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
